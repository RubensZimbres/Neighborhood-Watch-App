"""
Multi-agent orchestration layer for NeighborhoodAlert.

Turns the flat fetch+AI pipeline into an explicit DAG of named, isolated
"subagents" that run as topological waves on a background thread:

                  ┌──> weather ─────┐
                  ├──> nws ──────────┤ (nws merges into weather["alerts"])
    geocode  ─────┼──> crime ────────┼──> risk ──> ai_briefing
    (root)        ├──> infra ────────┤
                  └──> earthquakes ──┘

Design notes:
  • Pure Python (threading / concurrent.futures / dataclasses) — no new vendor.
  • DataFetcher / AIAnalyzer are injected as *instances* (no import cycle with
    utils.data_fetcher, which can import this module lazily).
  • Subagent bodies are thin closures over the EXISTING DataFetcher / AIAnalyzer
    methods — no fetch logic is reimplemented here.
  • Per-source error isolation: a failing source is marked FAILED, its on_error
    stub is substituted, and siblings/downstream continue (graceful degradation).
    The root (geocode) has no stub, so a geocode failure aborts and propagates.
  • The background thread writes ONLY to a thread-safe ProgressBoard — it never
    touches Streamlit (`st.*` / session_state). The Streamlit main thread polls
    board.snapshot() and re-renders.
"""

from __future__ import annotations

import copy
import threading
import time
import concurrent.futures
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


PROPAGATE = object()


class Status(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Subagent:
    """A named, isolated unit of work in the orchestration DAG.

    body(deps)      -> result. `deps` is {dep_name: that subagent's result}.
    on_error(deps)  -> substitute value when body raises (or a plain value, or
                       PROPAGATE to abort the whole run).
    """
    name: str
    body: Callable[[Dict[str, Any]], Any]
    deps: Tuple[str, ...] = ()
    on_error: Any = PROPAGATE


class ProgressBoard:
    """Thread-safe live status board shared between the worker thread and the UI.

    Only plain dicts/strings/ints cross the thread boundary (snapshot deep-copies),
    so the Streamlit main thread can read progress without touching worker state.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._rows: Dict[str, dict] = {}
        self._done = threading.Event()
        self._final: Any = None
        self._exc: Optional[BaseException] = None

    def init_row(self, name: str, deps: Tuple[str, ...]):
        with self._lock:
            self._rows[name] = {
                "name": name,
                "deps": list(deps),
                "status": Status.QUEUED.value,
                "elapsed_ms": None,
                "error": None,
            }

    def update(self, name: str, **fields):
        with self._lock:
            row = self._rows.setdefault(name, {"name": name})
            row.update(fields)

    def set_result(self, data: Any):
        self._final = data
        self._done.set()

    def set_error(self, exc: BaseException):
        self._exc = exc
        self._done.set()

    def snapshot(self) -> List[dict]:
        """Return a deep copy of the rows (plain dicts), in DAG insertion order."""
        with self._lock:
            return [copy.deepcopy(row) for row in self._rows.values()]

    def is_done(self) -> bool:
        return self._done.is_set()

    def result(self) -> Any:
        """Return the final assembled data, or re-raise the captured exception."""
        if self._exc is not None:
            raise self._exc
        return self._final


class Orchestrator:
    """Runs a set of Subagents as a topologically-ordered set of parallel waves."""

    def __init__(self, subagents: List[Subagent], board: ProgressBoard, max_workers: int = 5):
        self.subagents: Dict[str, Subagent] = {s.name: s for s in subagents}
        self.board = board
        self.max_workers = max_workers
        for s in subagents:
            self.board.init_row(s.name, s.deps)

    def run(self) -> Dict[str, Any]:
        """Execute the DAG and return {name: result}. Re-raises on a PROPAGATE failure."""
        results: Dict[str, Any] = {}
        remaining = dict(self.subagents)

        while remaining:
            ready = [s for s in remaining.values() if all(d in results for d in s.deps)]
            if not ready:
                raise RuntimeError(
                    "Orchestration deadlock — unsatisfiable dependencies among: "
                    + ", ".join(remaining)
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                futures = {ex.submit(self._run_one, s, results): s for s in ready}
                for fut in concurrent.futures.as_completed(futures):
                    name, value, error = fut.result()
                    if error is not None:
                        raise error
                    results[name] = value

            for s in ready:
                remaining.pop(s.name, None)

        return results

    def _run_one(self, s: Subagent, results: Dict[str, Any]):
        """Run one subagent with status/timing tracking and error isolation."""
        deps_data = {d: results[d] for d in s.deps}
        self.board.update(s.name, status=Status.RUNNING.value)
        start = time.monotonic()
        try:
            value = s.body(deps_data)
            self.board.update(
                s.name, status=Status.DONE.value,
                elapsed_ms=int((time.monotonic() - start) * 1000),
            )
            return (s.name, value, None)
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            self.board.update(s.name, status=Status.FAILED.value, elapsed_ms=elapsed, error=str(e))
            if s.on_error is PROPAGATE:
                return (s.name, None, e)
            stub = s.on_error(deps_data) if callable(s.on_error) else s.on_error
            return (s.name, stub, None)



def _core_data(deps: Dict[str, Any]) -> dict:
    """Assemble the data dict from subagent results (nws merged into weather)."""
    weather = dict(deps["weather"])
    weather["alerts"] = deps["nws"]
    return {
        "geo": deps["geocode"],
        "weather": weather,
        "crime": deps["crime"],
        "infrastructure": deps["infra"],
        "earthquakes": deps["earthquakes"],
        "risk_score": deps["risk"],
    }


def build_pipeline(address: str, fetcher, analyzer, board: ProgressBoard) -> Tuple[List[Subagent], Callable[[Dict[str, Any]], dict]]:
    """Construct the 8 subagents (closures over existing methods) + a final assembler.

    Returns (subagents, assemble) where assemble({name: result}) -> final data dict.
    """

    def geo_of(deps):
        return deps["geocode"]

    def city_key_of(geo) -> str:
        return fetcher._detect_city(geo.get("city", ""), geo.get("state", ""))

    subagents = [
        Subagent("geocode", lambda d: fetcher._geocode(address)),

        Subagent(
            "weather", lambda d: fetcher._fetch_weather(geo_of(d)["lat"], geo_of(d)["lon"]),
            deps=("geocode",),
            on_error=lambda d: fetcher._weather_stub(geo_of(d)["lat"], geo_of(d)["lon"]),
        ),
        Subagent(
            "nws", lambda d: fetcher._fetch_nws_alerts(geo_of(d)["lat"], geo_of(d)["lon"]),
            deps=("geocode",), on_error=lambda d: [],
        ),
        Subagent(
            "crime",
            lambda d: fetcher._fetch_crime(
                geo_of(d)["lat"], geo_of(d)["lon"], city_key_of(geo_of(d)),
                geo_of(d).get("state", ""), geo_of(d),
            ),
            deps=("geocode",),
            on_error=lambda d: {"incidents": [], "total_count": 0, "type_counts": {},
                                "fbi_stats": {}, "fbi_summary": {}, "period_days": 30},
        ),
        Subagent(
            "infra",
            lambda d: fetcher._fetch_311(geo_of(d)["lat"], geo_of(d)["lon"], city_key_of(geo_of(d))),
            deps=("geocode",),
            on_error=lambda d: {"complaints": [], "total": 0, "categories": {}},
        ),
        Subagent(
            "earthquakes", lambda d: fetcher._fetch_earthquakes(geo_of(d)["lat"], geo_of(d)["lon"]),
            deps=("geocode",), on_error=lambda d: [],
        ),

        Subagent(
            "risk",
            lambda d: fetcher._compute_risk(
                d["crime"], _merge_alerts(d["weather"], d["nws"]),
                d["infra"], d["earthquakes"], city_key_of(d["geocode"]),
            ),
            deps=("geocode", "weather", "nws", "crime", "infra", "earthquakes"),
            on_error=lambda d: {"overall": 0, "overall_label": "Low"},
        ),

        Subagent(
            "ai_briefing",
            lambda d: analyzer.analyze(_core_data(d), address),
            deps=("geocode", "weather", "nws", "crime", "infra", "earthquakes", "risk"),
            on_error=lambda d: "AI analysis unavailable.",
        ),
    ]

    def assemble(results: Dict[str, Any]) -> dict:
        data = _core_data(results)
        data["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"
        data["analysis"] = results.get("ai_briefing")
        return data

    return subagents, assemble


def _merge_alerts(weather: dict, nws: list) -> dict:
    merged = dict(weather)
    merged["alerts"] = nws
    return merged


def start_pipeline(address: str, fetcher, analyzer) -> ProgressBoard:
    """Non-blocking entry point: start the DAG on a daemon thread, return the board.

    The caller (Streamlit) polls board.snapshot()/is_done() and reads board.result()
    once done. The worker thread never touches Streamlit.
    """
    board = ProgressBoard()
    subagents, assemble = build_pipeline(address, fetcher, analyzer, board)
    orchestrator = Orchestrator(subagents, board)

    def _runner():
        try:
            board.set_result(assemble(orchestrator.run()))
        except Exception as e:
            board.set_error(e)

    threading.Thread(target=_runner, name=f"na-pipeline:{address[:24]}", daemon=True).start()
    return board
