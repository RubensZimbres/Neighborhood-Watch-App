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
