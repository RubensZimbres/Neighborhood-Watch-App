"""
Tests for utils/ai_analyzer.py

Covers:
  - AIAnalyzer.__init__: client initialization under various conditions
  - _build_prompt: correct address, data fields, section headers in output
  - _fallback_analysis: structure and content of the fallback response
  - _call_gemini: normal response, empty text, exception handling
  - analyze: routing between _call_gemini and _fallback_analysis
"""

import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))



def _make_full_data(overall=42, crime_count=15, weather_score=20, infra_count=5):
    return {
        "risk_score": {
            "overall": overall,
            "overall_label": "Moderate",
            "crime_score": 35,
            "crime_label": "Moderate",
            "weather_score": weather_score,
            "weather_label": "Low",
            "infra_score": 10,
            "infra_label": "Low",
        },
        "crime": {
            "total_count": crime_count,
            "type_counts": {"THEFT": 8, "BATTERY": 5, "ROBBERY": 2},
        },
        "weather": {
            "current": {
                "temp_f": 65, "feels_like_f": 62, "humidity": 60,
                "wind_mph": 12, "description": "Partly Cloudy",
            },
            "alerts": [],
        },
        "infrastructure": {
            "total": infra_count,
            "categories": {"Pothole in Street": 3, "Street Light Out": 2},
        },
        "earthquakes": [
            {"magnitude": 2.5, "place": "10km N of Test City", "time": "2024-01-10", "url": ""}
        ],
    }


def _make_analyzer_with_client():
    """Return an AIAnalyzer instance with a mock _client already set."""
    from utils.ai_analyzer import AIAnalyzer
    analyzer = AIAnalyzer.__new__(AIAnalyzer)
    analyzer._client = MagicMock()
    return analyzer



class TestAIAnalyzerInit:
    def test_no_gcp_project_no_api_key_client_is_none(self):
        with patch("utils.ai_analyzer.VERTEX_AVAILABLE", True), \
             patch.dict(os.environ, {}, clear=True):
            from utils.ai_analyzer import AIAnalyzer
            analyzer = AIAnalyzer()
        assert analyzer._client is None

    def test_vertex_unavailable_no_api_key_client_is_none(self):
        with patch("utils.ai_analyzer.VERTEX_AVAILABLE", False), \
             patch.dict(os.environ, {"GCP_PROJECT_NAME": "test-project"}, clear=True):
            from utils.ai_analyzer import AIAnalyzer
            analyzer = AIAnalyzer()
        assert analyzer._client is None

    def test_init_exception_leaves_client_none(self):
        mock_genai = MagicMock()
        mock_genai.Client.side_effect = Exception("Auth failed")
        with patch("utils.ai_analyzer.VERTEX_AVAILABLE", True), \
             patch("utils.ai_analyzer.genai", mock_genai, create=True), \
             patch.dict(os.environ, {"GCP_PROJECT_NAME": "test-project"}, clear=True):
            from utils.ai_analyzer import AIAnalyzer
            analyzer = AIAnalyzer()
        assert analyzer._client is None

    def test_api_key_fallback_constructs_client(self):
        mock_genai = MagicMock()
        with patch("utils.ai_analyzer.VERTEX_AVAILABLE", True), \
             patch("utils.ai_analyzer.genai", mock_genai, create=True), \
             patch.dict(os.environ, {"GOOGLE_AI_API_KEY": "k"}, clear=True):
            from utils.ai_analyzer import AIAnalyzer
            analyzer = AIAnalyzer()
        assert analyzer._client is not None
        mock_genai.Client.assert_called_once_with(api_key="k")



class TestBuildPrompt:
    def setup_method(self):
        from utils.ai_analyzer import AIAnalyzer
        self.analyzer = AIAnalyzer.__new__(AIAnalyzer)
        self.analyzer._client = None

    def test_address_appears_in_prompt(self):
        prompt = self.analyzer._build_prompt(_make_full_data(), "123 Main St, Chicago, IL")
        assert "123 Main St, Chicago, IL" in prompt

    def test_overall_risk_score_in_prompt(self):
        data = _make_full_data(overall=42)
        prompt = self.analyzer._build_prompt(data, "test")
        assert "42" in prompt

    def test_crime_count_in_prompt(self):
        data = _make_full_data(crime_count=15)
        prompt = self.analyzer._build_prompt(data, "test")
        assert "15" in prompt

    def test_crime_type_counts_in_prompt(self):
        prompt = self.analyzer._build_prompt(_make_full_data(), "test")
        assert "THEFT" in prompt

    def test_required_output_sections_in_prompt(self):
        prompt = self.analyzer._build_prompt(_make_full_data(), "test")
        assert "Overall Assessment" in prompt
        assert "Crime Intelligence" in prompt
        assert "Weather" in prompt
        assert "Infrastructure" in prompt
        assert "Recommended Actions" in prompt

    def test_empty_data_does_not_raise(self):
        prompt = self.analyzer._build_prompt({}, "test address")
        assert "test address" in prompt

    def test_weather_temp_in_prompt(self):
        data = _make_full_data()
        prompt = self.analyzer._build_prompt(data, "test")
        assert "65" in prompt

    def test_word_limit_instruction_in_prompt(self):
        prompt = self.analyzer._build_prompt(_make_full_data(), "test")
        assert "500 words" in prompt



class TestFallbackAnalysis:
    def setup_method(self):
        from utils.ai_analyzer import AIAnalyzer
        self.analyzer = AIAnalyzer.__new__(AIAnalyzer)
        self.analyzer._client = None

    def test_returns_string(self):
        result = self.analyzer._fallback_analysis(_make_full_data(), "Chicago, IL")
        assert isinstance(result, str)

    def test_contains_risk_label(self):
        result = self.analyzer._fallback_analysis(_make_full_data(overall=42), "test")
        assert "Moderate" in result

    def test_contains_crime_count(self):
        result = self.analyzer._fallback_analysis(_make_full_data(crime_count=15), "test")
        assert "15" in result

    def test_contains_all_section_headers(self):
        result = self.analyzer._fallback_analysis(_make_full_data(), "test")
        assert "Overall Assessment" in result
        assert "Crime Intelligence" in result
        assert "Weather" in result
        assert "Infrastructure" in result
        assert "Recommended Actions" in result

    def test_empty_data_does_not_raise(self):
        result = self.analyzer._fallback_analysis({}, "")
        assert isinstance(result, str)

    def test_contains_five_recommended_actions(self):
        result = self.analyzer._fallback_analysis(_make_full_data(), "test")
        for i in range(1, 6):
            assert f"{i}." in result



class TestCallGemini:
    """
    genai_types is patched to a MagicMock so all calls like
    genai_types.Content(...) / genai_types.Part.from_text(...) succeed
    regardless of the installed google-genai version.
    """

    def setup_method(self):
        self.analyzer = _make_analyzer_with_client()
        self._genai_types_patcher = patch("utils.ai_analyzer.genai_types", MagicMock())
        self._genai_types_patcher.start()

    def teardown_method(self):
        self._genai_types_patcher.stop()

    def test_returns_response_text(self):
        mock_response = MagicMock()
        mock_response.text = "AI safety briefing here."
        self.analyzer._client.models.generate_content.return_value = mock_response

        result = self.analyzer._call_gemini("test prompt")
        assert result == "AI safety briefing here."

    def test_empty_response_text_returns_fallback_message(self):
        mock_response = MagicMock()
        mock_response.text = ""
        self.analyzer._client.models.generate_content.return_value = mock_response

        result = self.analyzer._call_gemini("test prompt")
        assert result == "No analysis returned."

    def test_none_response_text_returns_fallback_message(self):
        mock_response = MagicMock()
        mock_response.text = None
        self.analyzer._client.models.generate_content.return_value = mock_response

        result = self.analyzer._call_gemini("test prompt")
        assert result == "No analysis returned."

    def test_exception_returns_error_string_with_fallback(self):
        self.analyzer._client.models.generate_content.side_effect = Exception("quota exceeded")

        result = self.analyzer._call_gemini("test prompt")
        assert "Gemini analysis failed" in result
        assert "quota exceeded" in result

    def test_passes_correct_model_name(self):
        mock_response = MagicMock()
        mock_response.text = "ok"
        self.analyzer._client.models.generate_content.return_value = mock_response

        from utils.ai_analyzer import GEMINI_MODEL
        self.analyzer._call_gemini("test prompt")

        call_kwargs = self.analyzer._client.models.generate_content.call_args[1]
        assert call_kwargs["model"] == GEMINI_MODEL

    def test_generate_content_called_once(self):
        mock_response = MagicMock()
        mock_response.text = "response"
        self.analyzer._client.models.generate_content.return_value = mock_response

        self.analyzer._call_gemini("prompt")
        self.analyzer._client.models.generate_content.assert_called_once()



class TestAnalyze:
    def test_no_client_calls_fallback(self):
        from utils.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer.__new__(AIAnalyzer)
        analyzer._client = None

        with patch.object(analyzer, "_fallback_analysis", return_value="fallback") as mock_fb, \
             patch.object(analyzer, "_call_gemini") as mock_gemini:
            result = analyzer.analyze(_make_full_data(), "Chicago, IL")

        mock_fb.assert_called_once()
        mock_gemini.assert_not_called()
        assert result == "fallback"

    def test_with_client_calls_gemini(self):
        analyzer = _make_analyzer_with_client()

        with patch.object(analyzer, "_call_gemini", return_value="gemini result") as mock_gemini, \
             patch.object(analyzer, "_fallback_analysis") as mock_fb:
            result = analyzer.analyze(_make_full_data(), "Chicago, IL")

        mock_gemini.assert_called_once()
        mock_fb.assert_not_called()
        assert result == "gemini result"

    def test_address_passed_to_prompt_builder(self):
        from utils.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer.__new__(AIAnalyzer)
        analyzer._client = None

        with patch.object(analyzer, "_build_prompt", return_value="prompt") as mock_build, \
             patch.object(analyzer, "_fallback_analysis", return_value=""):
            analyzer.analyze(_make_full_data(), "789 Oak Ave, Denver, CO")

        call_args = mock_build.call_args
        assert call_args[0][1] == "789 Oak Ave, Denver, CO"

    def test_data_passed_to_prompt_builder(self):
        from utils.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer.__new__(AIAnalyzer)
        analyzer._client = None
        data = _make_full_data(overall=77)

        with patch.object(analyzer, "_build_prompt", return_value="prompt") as mock_build, \
             patch.object(analyzer, "_fallback_analysis", return_value=""):
            analyzer.analyze(data, "test")

        assert mock_build.call_args[0][0] is data
