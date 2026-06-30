import sys
import os
import time
import threading
import pytest
import requests
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from google.adk.agents import SequentialAgent, ParallelAgent

from utils.data_fetcher import DataFetcher
from utils.ai_analyzer import AIAnalyzer
from utils.orchestration import (
    Status,
    NodeAgent,
    ProgressBoard,
    build_pipeline,
    run_pipeline,
    start_pipeline,
    PROPAGATE,
)

ALL_KEYS = {"geo", "weather", "crime", "infrastructure",
            "earthquakes", "risk_score", "fetched_at", "analysis"}


def _run_sync(fetcher, analyzer, address="Chicago, IL"):
    board = ProgressBoard()
    root, assemble_fn = build_pipeline(address, fetcher, analyzer, board)
    state = run_pipeline(root)
    return assemble_fn(state), board


def _rows_by_name(board):
    return {r["name"]: r for r in board.snapshot()}


def _node(name, body, deps=(), on_error=PROPAGATE, board=None):
    return NodeAgent(name=name, body=body, node_deps=deps, on_error=on_error, board=board)



class TestProgressBoard:
    def test_snapshot_returns_plain_copies(self):
        b = ProgressBoard()
        b.init_row("x", ("dep",))
        snap1 = b.snapshot()
        snap1[0]["status"] = "mutated"
        assert b.snapshot()[0]["status"] == Status.QUEUED.value

    def test_result_reraises_stored_exception(self):
        b = ProgressBoard()
        b.set_error(ValueError("boom"))
        assert b.is_done()
        with pytest.raises(ValueError, match="boom"):
            b.result()

    def test_result_returns_final(self):
        b = ProgressBoard()
        b.set_result({"ok": 1})
        assert b.is_done()
        assert b.result() == {"ok": 1}



class TestNodeAgentGeneric:
    def test_runs_in_topological_order(self):
        board = ProgressBoard()
        order = []
        a = _node("a", lambda d: order.append("a") or "A", board=board)
        b = _node("b", lambda d: order.append("b") or "B", deps=("a",), board=board)
        c = _node("c", lambda d: order.append("c") or "C", deps=("b",), board=board)
        root = SequentialAgent(name="r", sub_agents=[a, b, c])

        state = run_pipeline(root)
        assert state == {"a": "A", "b": "B", "c": "C"}
        assert order == ["a", "b", "c"]

    def test_deps_data_passed_to_body(self):
        board = ProgressBoard()
        captured = {}
        a = _node("a", lambda d: 41, board=board)
        b = _node("b", lambda d: captured.update(d) or d["a"] + 1, deps=("a",), board=board)
        run_pipeline(SequentialAgent(name="r", sub_agents=[a, b]))
        assert captured == {"a": 41}

    def test_stub_substituted_on_failure(self):
        def boom(d):
            raise RuntimeError("nope")
        board = ProgressBoard()
        board.init_row("a", ())
        board.init_row("b", ("a",))
        a = _node("a", boom, on_error=lambda d: "STUB", board=board)
        b = _node("b", lambda d: d["a"] + "!", deps=("a",), board=board)

        state = run_pipeline(SequentialAgent(name="r", sub_agents=[a, b]))
        assert state["b"] == "STUB!"
        assert _rows_by_name(board)["a"]["status"] == Status.FAILED.value

    def test_propagate_node_aborts_run(self):
        def boom(d):
            raise ValueError("fatal")
        board = ProgressBoard()
        board.init_row("a", ())
        board.init_row("b", ("a",))
        a = _node("a", boom, on_error=PROPAGATE, board=board)
        b = _node("b", lambda d: "B", deps=("a",), board=board)

        with pytest.raises(ValueError, match="fatal"):
            run_pipeline(SequentialAgent(name="r", sub_agents=[a, b]))
        rows = _rows_by_name(board)
        assert rows["a"]["status"] == Status.FAILED.value
        assert rows["b"]["status"] == Status.QUEUED.value

    def test_parallel_children_share_state(self):
        board = ProgressBoard()
        root_node = _node("root", lambda d: {"v": 7}, board=board)
        left = _node("left", lambda d: d["root"]["v"] + 1, deps=("root",), board=board)
        right = _node("right", lambda d: d["root"]["v"] + 2, deps=("root",), board=board)
        merge = _node("merge", lambda d: d["left"] + d["right"],
                      deps=("root", "left", "right"), board=board)
        sources = ParallelAgent(name="s", sub_agents=[left, right])
        state = run_pipeline(SequentialAgent(name="r", sub_agents=[root_node, sources, merge]))
        assert state["merge"] == 17



class TestPipelineOrdering:
    @patch.object(AIAnalyzer, "analyze")
    @patch.object(DataFetcher, "_compute_risk")
    @patch.object(DataFetcher, "_fetch_earthquakes")
    @patch.object(DataFetcher, "_fetch_311")
    @patch.object(DataFetcher, "_fetch_crime")
    @patch.object(DataFetcher, "_fetch_nws_alerts")
    @patch.object(DataFetcher, "_fetch_weather")
    @patch.object(DataFetcher, "_geocode")
    def test_risk_after_sources_ai_last(
        self, mock_geo, mock_weather, mock_nws, mock_crime, mock_311,
        mock_quakes, mock_risk, mock_analyze,
        geo_chicago, weather_clear, crime_empty, infra_empty,
    ):
        order = []
        lock = threading.Lock()

        def rec(name, ret):
            def _se(*a, **k):
                with lock:
                    order.append(name)
                return ret
            return _se

        mock_geo.side_effect = rec("geocode", geo_chicago)
        mock_weather.side_effect = rec("weather", weather_clear)
        mock_nws.side_effect = rec("nws", [])
        mock_crime.side_effect = rec("crime", crime_empty)
        mock_311.side_effect = rec("infra", infra_empty)
        mock_quakes.side_effect = rec("earthquakes", [])
        mock_risk.side_effect = rec("risk", {"overall": 5, "overall_label": "Low"})
        mock_analyze.side_effect = rec("ai", "briefing")

        data, board = _run_sync(DataFetcher(), AIAnalyzer())

        assert order[0] == "geocode"
        risk_idx = order.index("risk")
        for src in ("weather", "nws", "crime", "infra", "earthquakes"):
            assert order.index(src) < risk_idx
        assert order[-1] == "ai"

        assert set(data.keys()) == ALL_KEYS
        assert data["analysis"] == "briefing"
        assert data["risk_score"] == {"overall": 5, "overall_label": "Low"}
        assert data["fetched_at"].endswith("Z")

    @patch.object(AIAnalyzer, "analyze", return_value="briefing")
    @patch.object(DataFetcher, "_fetch_earthquakes", return_value=[])
    @patch.object(DataFetcher, "_fetch_311")
    @patch.object(DataFetcher, "_fetch_crime")
    @patch.object(DataFetcher, "_fetch_nws_alerts")
    @patch.object(DataFetcher, "_fetch_weather")
    @patch.object(DataFetcher, "_geocode")
    def test_city_key_passed_to_crime_and_311(
        self, mock_geo, mock_weather, mock_nws, mock_crime, mock_311, mock_quakes,
        mock_analyze, geo_chicago, weather_clear, crime_empty, infra_empty,
    ):
        mock_geo.return_value = geo_chicago
        mock_weather.return_value = weather_clear
        mock_nws.return_value = []
        mock_crime.return_value = crime_empty
        mock_311.return_value = infra_empty

        _run_sync(DataFetcher(), AIAnalyzer())

        assert mock_crime.call_args[0][2] == "chicago"
        assert mock_311.call_args[0][2] == "chicago"

    @patch.object(AIAnalyzer, "analyze", return_value="briefing")
    @patch.object(DataFetcher, "_fetch_earthquakes", return_value=[])
    @patch.object(DataFetcher, "_fetch_311")
    @patch.object(DataFetcher, "_fetch_crime")
    @patch.object(DataFetcher, "_fetch_nws_alerts")
    @patch.object(DataFetcher, "_fetch_weather")
    @patch.object(DataFetcher, "_geocode")
    def test_nws_merged_into_weather(
        self, mock_geo, mock_weather, mock_nws, mock_crime, mock_311, mock_quakes,
        mock_analyze, geo_chicago, weather_clear, crime_empty, infra_empty,
    ):
        mock_geo.return_value = geo_chicago
        mock_weather.return_value = dict(weather_clear)
        mock_nws.return_value = [{"event": "Test Alert", "severity": "Moderate"}]
        mock_crime.return_value = crime_empty
        mock_311.return_value = infra_empty

        data, _ = _run_sync(DataFetcher(), AIAnalyzer())
        assert data["weather"]["alerts"] == [{"event": "Test Alert", "severity": "Moderate"}]



class TestErrorIsolation:
    @patch.object(AIAnalyzer, "analyze", return_value="briefing")
    @patch.object(DataFetcher, "_fetch_earthquakes", return_value=[])
    @patch.object(DataFetcher, "_fetch_311")
    @patch.object(DataFetcher, "_fetch_crime")
    @patch.object(DataFetcher, "_fetch_nws_alerts", return_value=[])
    @patch.object(DataFetcher, "_fetch_weather")
    @patch.object(DataFetcher, "_geocode")
    def test_failing_source_isolated_siblings_continue(
        self, mock_geo, mock_weather, mock_nws, mock_crime, mock_311, mock_quakes,
        mock_analyze, geo_chicago, weather_clear, infra_empty,
    ):
        mock_geo.return_value = geo_chicago
        mock_weather.return_value = weather_clear
        mock_crime.side_effect = requests.HTTPError("crime feed down")
        mock_311.return_value = infra_empty

        data, board = _run_sync(DataFetcher(), AIAnalyzer())
        rows = _rows_by_name(board)

        assert rows["crime"]["status"] == Status.FAILED.value
        assert "crime feed down" in rows["crime"]["error"]
        assert rows["weather"]["status"] == Status.DONE.value
        assert rows["infra"]["status"] == Status.DONE.value

        assert data["crime"]["total_count"] == 0
        assert set(data.keys()) == ALL_KEYS
        assert data["analysis"] == "briefing"

    @patch.object(AIAnalyzer, "analyze", side_effect=RuntimeError("model down"))
    @patch.object(DataFetcher, "_compute_risk", return_value={"overall": 0, "overall_label": "Low"})
    @patch.object(DataFetcher, "_fetch_earthquakes", return_value=[])
    @patch.object(DataFetcher, "_fetch_311")
    @patch.object(DataFetcher, "_fetch_crime")
    @patch.object(DataFetcher, "_fetch_nws_alerts", return_value=[])
    @patch.object(DataFetcher, "_fetch_weather")
    @patch.object(DataFetcher, "_geocode")
    def test_ai_failure_falls_back(
        self, mock_geo, mock_weather, mock_nws, mock_crime, mock_311, mock_quakes,
        mock_risk, mock_analyze, geo_chicago, weather_clear, crime_empty, infra_empty,
    ):
        mock_geo.return_value = geo_chicago
        mock_weather.return_value = weather_clear
        mock_crime.return_value = crime_empty
        mock_311.return_value = infra_empty

        data, board = _run_sync(DataFetcher(), AIAnalyzer())
        rows = _rows_by_name(board)
        assert rows["ai_briefing"]["status"] == Status.FAILED.value
        assert data["analysis"] == "AI analysis unavailable."



class TestRootFailure:
    @patch.object(DataFetcher, "_fetch_weather")
    @patch.object(DataFetcher, "_geocode")
    def test_geocode_failure_propagates_and_downstream_queued(self, mock_geo, mock_weather):
        mock_geo.side_effect = ValueError("Could not geocode: xyz")

        board = ProgressBoard()
        root, _ = build_pipeline("xyz", DataFetcher(), AIAnalyzer(), board)
        with pytest.raises(ValueError, match="Could not geocode"):
            run_pipeline(root)

        rows = _rows_by_name(board)
        assert rows["geocode"]["status"] == Status.FAILED.value
        assert rows["weather"]["status"] == Status.QUEUED.value
        assert rows["ai_briefing"]["status"] == Status.QUEUED.value
        mock_weather.assert_not_called()



class TestStatusTransitions:
    @patch.object(AIAnalyzer, "analyze", return_value="briefing")
    @patch.object(DataFetcher, "_fetch_earthquakes", return_value=[])
    @patch.object(DataFetcher, "_fetch_311")
    @patch.object(DataFetcher, "_fetch_crime")
    @patch.object(DataFetcher, "_fetch_nws_alerts", return_value=[])
    @patch.object(DataFetcher, "_fetch_weather")
    @patch.object(DataFetcher, "_geocode")
    def test_terminal_rows_done_with_elapsed(
        self, mock_geo, mock_weather, mock_nws, mock_crime, mock_311, mock_quakes,
        mock_analyze, geo_chicago, weather_clear, crime_empty, infra_empty,
    ):
        mock_geo.return_value = geo_chicago
        mock_weather.return_value = weather_clear
        mock_crime.return_value = crime_empty
        mock_311.return_value = infra_empty

        _, board = _run_sync(DataFetcher(), AIAnalyzer())
        for r in board.snapshot():
            assert r["status"] in (Status.DONE.value, Status.FAILED.value)
            assert r["elapsed_ms"] is not None
            assert r["elapsed_ms"] >= 0

    def test_running_status_observable_mid_flight(self):
        started = threading.Event()
        release = threading.Event()

        def slow(d):
            started.set()
            release.wait(2)
            return "done"

        board = ProgressBoard()
        board.init_row("slow", ())
        node = _node("slow", slow, board=board)
        root = SequentialAgent(name="r", sub_agents=[node])

        t = threading.Thread(target=run_pipeline, args=(root,), daemon=True)
        t.start()
        try:
            assert started.wait(2)
            assert _rows_by_name(board)["slow"]["status"] == Status.RUNNING.value
        finally:
            release.set()
            t.join(2)
        assert _rows_by_name(board)["slow"]["status"] == Status.DONE.value



class TestStartPipeline:
    @patch.object(AIAnalyzer, "analyze", return_value="briefing")
    @patch.object(DataFetcher, "_fetch_earthquakes", return_value=[])
    @patch.object(DataFetcher, "_fetch_311")
    @patch.object(DataFetcher, "_fetch_crime")
    @patch.object(DataFetcher, "_fetch_nws_alerts", return_value=[])
    @patch.object(DataFetcher, "_fetch_weather")
    @patch.object(DataFetcher, "_geocode")
    def test_background_run_completes_with_plain_snapshot(
        self, mock_geo, mock_weather, mock_nws, mock_crime, mock_311, mock_quakes,
        mock_analyze, geo_chicago, weather_clear, crime_empty, infra_empty,
    ):
        mock_geo.return_value = geo_chicago
        mock_weather.return_value = weather_clear
        mock_crime.return_value = crime_empty
        mock_311.return_value = infra_empty

        board = start_pipeline("Chicago, IL", DataFetcher(), AIAnalyzer())

        deadline = time.monotonic() + 5
        while not board.is_done() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert board.is_done()

        snap = board.snapshot()
        assert len(snap) == 8
        for r in snap:
            assert isinstance(r, dict)
            assert isinstance(r["status"], str)
            assert isinstance(r["deps"], list)

        data = board.result()
        assert set(data.keys()) == ALL_KEYS
        assert data["analysis"] == "briefing"
