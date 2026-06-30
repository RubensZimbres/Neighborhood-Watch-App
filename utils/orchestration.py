import asyncio
import copy
import threading
import time
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

from pydantic import ConfigDict

from google.adk.agents import BaseAgent, ParallelAgent, SequentialAgent
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


PROPAGATE = object()

_APP_NAME = "neighborhood_alert"
_USER_ID = "local"
_SESSION_ID = "pipeline"


class Status(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ProgressBoard:

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
        with self._lock:
            return [copy.deepcopy(row) for row in self._rows.values()]

    def is_done(self) -> bool:
        return self._done.is_set()

    def result(self) -> Any:
        if self._exc is not None:
            raise self._exc
        return self._final


class NodeAgent(BaseAgent):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    body: Any
    node_deps: Tuple[str, ...] = ()
    on_error: Any = PROPAGATE
    board: Any = None

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        deps_data = {d: ctx.session.state[d] for d in self.node_deps}
        self.board.update(self.name, status=Status.RUNNING.value)
        start = time.monotonic()
        try:
            value = await asyncio.to_thread(self.body, deps_data)
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            self.board.update(self.name, status=Status.FAILED.value, elapsed_ms=elapsed, error=str(e))
            if self.on_error is PROPAGATE:
                raise
            stub = self.on_error(deps_data) if callable(self.on_error) else self.on_error
            yield Event(author=self.name, actions=EventActions(state_delta={self.name: stub}))
            return
        self.board.update(
            self.name, status=Status.DONE.value,
            elapsed_ms=int((time.monotonic() - start) * 1000),
        )
        yield Event(author=self.name, actions=EventActions(state_delta={self.name: value}))


def _merge_alerts(weather: dict, nws: list) -> dict:
    merged = dict(weather)
    merged["alerts"] = nws
    return merged


def _core_data(deps: Dict[str, Any]) -> dict:
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


def assemble(state: Dict[str, Any]) -> dict:
    data = _core_data(state)
    data["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"
    data["analysis"] = state.get("ai_briefing")
    return data


def build_pipeline(address: str, fetcher, analyzer, board: ProgressBoard) -> Tuple[BaseAgent, Callable[[Dict[str, Any]], dict]]:

    def geo_of(deps):
        return deps["geocode"]

    def city_key_of(geo) -> str:
        return fetcher._detect_city(geo.get("city", ""), geo.get("state", ""))

    geocode = NodeAgent(
        name="geocode",
        body=lambda d: fetcher._geocode(address),
        board=board,
    )
    weather = NodeAgent(
        name="weather",
        body=lambda d: fetcher._fetch_weather(geo_of(d)["lat"], geo_of(d)["lon"]),
        node_deps=("geocode",),
        on_error=lambda d: fetcher._weather_stub(geo_of(d)["lat"], geo_of(d)["lon"]),
        board=board,
    )
    nws = NodeAgent(
        name="nws",
        body=lambda d: fetcher._fetch_nws_alerts(geo_of(d)["lat"], geo_of(d)["lon"]),
        node_deps=("geocode",),
        on_error=lambda d: [],
        board=board,
    )
    crime = NodeAgent(
        name="crime",
        body=lambda d: fetcher._fetch_crime(
            geo_of(d)["lat"], geo_of(d)["lon"], city_key_of(geo_of(d)),
            geo_of(d).get("state", ""), geo_of(d),
        ),
        node_deps=("geocode",),
        on_error=lambda d: {"incidents": [], "total_count": 0, "type_counts": {},
                            "fbi_stats": {}, "fbi_summary": {}, "period_days": 30},
        board=board,
    )
    infra = NodeAgent(
        name="infra",
        body=lambda d: fetcher._fetch_311(geo_of(d)["lat"], geo_of(d)["lon"], city_key_of(geo_of(d))),
        node_deps=("geocode",),
        on_error=lambda d: {"complaints": [], "total": 0, "categories": {}},
        board=board,
    )
    earthquakes = NodeAgent(
        name="earthquakes",
        body=lambda d: fetcher._fetch_earthquakes(geo_of(d)["lat"], geo_of(d)["lon"]),
        node_deps=("geocode",),
        on_error=lambda d: [],
        board=board,
    )
    risk = NodeAgent(
        name="risk",
        body=lambda d: fetcher._compute_risk(
            d["crime"], _merge_alerts(d["weather"], d["nws"]),
            d["infra"], d["earthquakes"], city_key_of(d["geocode"]),
        ),
        node_deps=("geocode", "weather", "nws", "crime", "infra", "earthquakes"),
        on_error=lambda d: {"overall": 0, "overall_label": "Low"},
        board=board,
    )
    ai_briefing = NodeAgent(
        name="ai_briefing",
        body=lambda d: analyzer.analyze(_core_data(d), address),
        node_deps=("geocode", "weather", "nws", "crime", "infra", "earthquakes", "risk"),
        on_error=lambda d: "AI analysis unavailable.",
        board=board,
    )

    nodes = [geocode, weather, nws, crime, infra, earthquakes, risk, ai_briefing]
    for node in nodes:
        board.init_row(node.name, node.node_deps)

    sources = ParallelAgent(name="sources", sub_agents=[weather, nws, crime, infra, earthquakes])
    root = SequentialAgent(name="pipeline", sub_agents=[geocode, sources, risk, ai_briefing])
    return root, assemble


async def _drive(root: BaseAgent) -> Dict[str, Any]:
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=_APP_NAME, user_id=_USER_ID, session_id=_SESSION_ID,
    )
    runner = Runner(app_name=_APP_NAME, agent=root, session_service=session_service)
    message = types.Content(role="user", parts=[types.Part.from_text(text="run")])
    async for _event in runner.run_async(
        user_id=_USER_ID, session_id=_SESSION_ID, new_message=message,
    ):
        pass
    session = await session_service.get_session(
        app_name=_APP_NAME, user_id=_USER_ID, session_id=_SESSION_ID,
    )
    return dict(session.state)


def run_pipeline(root: BaseAgent) -> Dict[str, Any]:
    return asyncio.run(_drive(root))


def start_pipeline(address: str, fetcher, analyzer) -> ProgressBoard:
    board = ProgressBoard()
    root, assemble_fn = build_pipeline(address, fetcher, analyzer, board)

    def _runner():
        try:
            state = run_pipeline(root)
            board.set_result(assemble_fn(state))
        except Exception as e:
            board.set_error(e)

    threading.Thread(target=_runner, name=f"na-pipeline:{address[:24]}", daemon=True).start()
    return board
