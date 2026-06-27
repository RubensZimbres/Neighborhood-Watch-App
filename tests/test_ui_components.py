"""
Tests for components/ui_components.py — HTML escaping security.
"""

from unittest.mock import patch, MagicMock
from components.ui_components import _esc
from utils.data_fetcher import DataFetcher



class TestEscHelper:
    def test_escapes_angle_brackets(self):
        assert _esc("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"

    def test_escapes_ampersand(self):
        assert _esc("A & B") == "A &amp; B"

    def test_escapes_double_quotes(self):
        assert _esc('he said "hello"') == "he said &quot;hello&quot;"

    def test_escapes_single_quotes(self):
        assert _esc("it's") == "it&#x27;s"

    def test_converts_non_strings(self):
        assert _esc(42) == "42"
        assert _esc(None) == "None"
        assert _esc(3.14) == "3.14"

    def test_passthrough_safe_text(self):
        assert _esc("Normal text") == "Normal text"

    def test_xss_payload_img_onerror(self):
        payload = '<img src=x onerror=alert(1)>'
        escaped = _esc(payload)
        assert "<" not in escaped
        assert ">" not in escaped
        assert escaped.startswith("&lt;")

    def test_xss_payload_event_handler(self):
        payload = '" onmouseover="alert(1)'
        escaped = _esc(payload)
        assert '"' not in escaped



class TestDetectCityImproved:
    def test_exact_match(self):
        assert DataFetcher._detect_city("Chicago", "") == "chicago"

    def test_compound_name_startswith(self):
        assert DataFetcher._detect_city("New York City", "") == "new york"

    def test_no_substring_false_positive(self):
        assert DataFetcher._detect_city("Austin", "") == "austin"

    def test_unsupported_city(self):
        assert DataFetcher._detect_city("Springfield", "") == ""

    def test_empty_string(self):
        assert DataFetcher._detect_city("", "") == ""

    def test_whitespace_handling(self):
        assert DataFetcher._detect_city("  Chicago  ", "") == "chicago"



class TestSafeGet:
    @patch("utils.data_fetcher.requests.get")
    @patch("utils.data_fetcher.time.sleep")
    def test_retries_on_500(self, mock_sleep, mock_get):
        fail_resp = MagicMock(status_code=500)
        ok_resp = MagicMock(status_code=200)
        mock_get.side_effect = [fail_resp, ok_resp]
        result = DataFetcher._safe_get("http://example.com", retries=1)
        assert result.status_code == 200
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch("utils.data_fetcher.requests.get")
    def test_returns_immediately_on_success(self, mock_get):
        ok_resp = MagicMock(status_code=200)
        mock_get.return_value = ok_resp
        result = DataFetcher._safe_get("http://example.com", retries=1)
        assert result.status_code == 200
        assert mock_get.call_count == 1

    @patch("utils.data_fetcher.requests.get")
    @patch("utils.data_fetcher.time.sleep")
    def test_retries_on_connection_error(self, mock_sleep, mock_get):
        ok_resp = MagicMock(status_code=200)
        mock_get.side_effect = [ConnectionError("fail"), ok_resp]
        import requests as req
        mock_get.side_effect = [req.ConnectionError("fail"), ok_resp]
        result = DataFetcher._safe_get("http://example.com", retries=1)
        assert result.status_code == 200

    @patch("utils.data_fetcher.requests.get")
    def test_no_retry_on_4xx(self, mock_get):
        resp = MagicMock(status_code=404)
        mock_get.return_value = resp
        result = DataFetcher._safe_get("http://example.com", retries=1)
        assert result.status_code == 404
        assert mock_get.call_count == 1



class TestRenderAgentTrace:
    def _render(self, rows):
        import components.ui_components as ui
        captured = []
        with patch.object(ui, "st") as mock_st:
            mock_st.markdown.side_effect = lambda html, **k: captured.append(html)
            ui.render_agent_trace(rows)
        return captured

    def test_single_markdown_call_no_newlines(self):
        rows = [
            {"name": "geocode", "deps": [], "status": "done", "elapsed_ms": 5, "error": None},
            {"name": "weather", "deps": ["geocode"], "status": "done", "elapsed_ms": 0, "error": None},
        ]
        calls = self._render(rows)
        assert len(calls) == 1
        assert "\n" not in calls[0]

    def test_emits_expected_structure(self):
        rows = [{"name": "geocode", "deps": [], "status": "done", "elapsed_ms": 5, "error": None}]
        html = self._render(rows)[0]
        assert html.startswith('<div class="amap">')
        assert html.endswith("</div>")
        assert '<div class="amap-name">Geocode</div>' in html
        assert "<b>1</b>/1 agents" in html
        assert '<div class="amap-bar-fill" style="width:100%"></div>' in html

    def test_stages_grouped_with_parallel_fanout(self):
        rows = [
            {"name": "geocode", "deps": [], "status": "done", "elapsed_ms": 5, "error": None},
            {"name": "weather", "deps": ["geocode"], "status": "done", "elapsed_ms": 1, "error": None},
            {"name": "crime", "deps": ["geocode"], "status": "done", "elapsed_ms": 1, "error": None},
            {"name": "risk", "deps": ["geocode", "weather", "crime"], "status": "running",
             "elapsed_ms": None, "error": None},
        ]
        html = self._render(rows)[0]
        assert "amap-stage parallel" in html
        assert "2 parallel agents" in html
        assert "amap-link" in html

    def test_running_shows_spinner_failed_shows_error(self):
        rows = [
            {"name": "risk", "deps": ["geocode"], "status": "running", "elapsed_ms": None, "error": None},
            {"name": "crime", "deps": ["geocode"], "status": "failed", "elapsed_ms": 9, "error": "feed down"},
        ]
        html = self._render(rows)[0]
        assert "amap-node is-running" in html
        assert '<span class="amap-spin2"></span>' in html
        assert "amap-node is-failed" in html
        assert 'class="amap-err"' in html and "feed down" in html

    def test_error_text_is_escaped(self):
        rows = [{"name": "crime", "deps": ["geocode"], "status": "failed",
                 "elapsed_ms": 1, "error": "<script>x</script>"}]
        html = self._render(rows)[0]
        assert "<script>x</script>" not in html
        assert "&lt;script&gt;" in html

    def test_elapsed_formatting(self):
        rows = [
            {"name": "geocode", "deps": [], "status": "done", "elapsed_ms": 5, "error": None},
            {"name": "weather", "deps": ["geocode"], "status": "done", "elapsed_ms": 1500, "error": None},
        ]
        html = self._render(rows)[0]
        assert "5 ms" in html
        assert "1.5s" in html

    def test_empty_rows_safe(self):
        calls = self._render([])
        assert len(calls) == 1
        assert "<b>0</b>/0 agents" in calls[0]
