"""
Tests for utils/data_fetcher.py

Covers:
  - Pure static helpers: _score_label, _detect_city
  - Module-level constants: STATE_ABBREVS, CITY_POPULATIONS
  - Risk computation: _compute_risk (per-capita scoring, weather, quakes, overall)
  - Geocoding: _geocode (mocked HTTP)
  - Weather: _fetch_weather, _weather_stub (mocked HTTP)
  - NWS alerts: _fetch_nws_alerts (mocked HTTP)
  - FBI stats: _fetch_fbi_stats (mocked HTTP + patched API key)
  - Socrata crime: _fetch_socrata_crime (mocked HTTP)
  - 311 infra: _fetch_311_city, _fetch_311 (mocked HTTP)
  - Earthquakes: _fetch_earthquakes (mocked HTTP)
  - Crime aggregation: _fetch_crime (mocked sub-calls)
  - Integration: fetch_all (all sub-calls mocked)
"""

import sys
import os
import pytest
import requests
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.data_fetcher import (
    DataFetcher,
    STATE_ABBREVS,
    CITY_POPULATIONS,
    DEFAULT_POPULATION,
)
from tests.conftest import make_ok_response, make_error_response



def _fetcher():
    return DataFetcher()


def _make_crime(total_count, type_counts=None):
    return {
        "incidents": [],
        "total_count": total_count,
        "type_counts": type_counts or {},
        "fbi_stats": {},
        "period_days": 30,
    }


def _make_infra(total):
    return {"complaints": [], "total": total, "categories": {}}


def _make_weather(alerts=None, wind_mph=0):
    return {
        "current": {"wind_mph": wind_mph},
        "forecast": [],
        "alerts": alerts if alerts is not None else [],
    }


def _make_alert(severity):
    return {"event": "Test", "severity": severity, "headline": "", "description": "", "onset": "", "expires": ""}



class TestScoreLabel:
    def test_zero_is_low(self):
        assert DataFetcher._score_label(0) == "Low"

    def test_boundary_below_moderate(self):
        assert DataFetcher._score_label(24) == "Low"

    def test_boundary_at_moderate(self):
        assert DataFetcher._score_label(25) == "Moderate"

    def test_middle_moderate(self):
        assert DataFetcher._score_label(37) == "Moderate"

    def test_boundary_below_high(self):
        assert DataFetcher._score_label(49) == "Moderate"

    def test_boundary_at_high(self):
        assert DataFetcher._score_label(50) == "High"

    def test_middle_high(self):
        assert DataFetcher._score_label(62) == "High"

    def test_boundary_below_critical(self):
        assert DataFetcher._score_label(74) == "High"

    def test_boundary_at_critical(self):
        assert DataFetcher._score_label(75) == "Critical"

    def test_100_is_critical(self):
        assert DataFetcher._score_label(100) == "Critical"



class TestDetectCity:
    def test_chicago(self):
        assert DataFetcher._detect_city("Chicago", "Illinois") == "chicago"

    def test_new_york(self):
        assert DataFetcher._detect_city("New York", "New York") == "new york"

    def test_los_angeles(self):
        assert DataFetcher._detect_city("Los Angeles", "California") == "los angeles"

    def test_san_francisco(self):
        assert DataFetcher._detect_city("San Francisco", "California") == "san francisco"

    def test_seattle(self):
        assert DataFetcher._detect_city("Seattle", "Washington") == "seattle"

    def test_dallas(self):
        assert DataFetcher._detect_city("Dallas", "Texas") == "dallas"

    def test_austin(self):
        assert DataFetcher._detect_city("Austin", "Texas") == "austin"

    def test_denver(self):
        assert DataFetcher._detect_city("Denver", "Colorado") == "denver"

    def test_houston(self):
        assert DataFetcher._detect_city("Houston", "Texas") == "houston"

    def test_boston(self):
        assert DataFetcher._detect_city("Boston", "Massachusetts") == "boston"

    def test_unsupported_city_returns_empty(self):
        assert DataFetcher._detect_city("Springfield", "Illinois") == ""

    def test_empty_city_returns_empty(self):
        assert DataFetcher._detect_city("", "") == ""

    def test_case_insensitive(self):
        assert DataFetcher._detect_city("CHICAGO", "Illinois") == "chicago"

    def test_substring_match_new_york_city(self):
        assert DataFetcher._detect_city("New York City", "New York") == "new york"

    def test_partial_unsupported(self):
        result = DataFetcher._detect_city("San Jose", "California")
        assert result != "san francisco"



class TestStateAbbrevs:
    def test_all_50_states_plus_dc(self):
        assert len(STATE_ABBREVS) == 51

    def test_illinois_maps_to_il(self):
        assert STATE_ABBREVS["Illinois"] == "IL"

    def test_california_maps_to_ca(self):
        assert STATE_ABBREVS["California"] == "CA"

    def test_new_york_maps_to_ny(self):
        assert STATE_ABBREVS["New York"] == "NY"

    def test_texas_maps_to_tx(self):
        assert STATE_ABBREVS["Texas"] == "TX"

    def test_district_of_columbia_maps_to_dc(self):
        assert STATE_ABBREVS["District of Columbia"] == "DC"

    def test_all_values_are_two_chars(self):
        assert all(len(v) == 2 for v in STATE_ABBREVS.values())

    def test_all_values_are_uppercase(self):
        assert all(v == v.upper() for v in STATE_ABBREVS.values())



class TestCityPopulations:
    def test_all_10_cities_present(self):
        expected = {
            "chicago", "new york", "los angeles", "san francisco", "seattle",
            "dallas", "austin", "denver", "houston", "boston",
        }
        assert set(CITY_POPULATIONS.keys()) == expected

    def test_populations_are_positive(self):
        assert all(v > 0 for v in CITY_POPULATIONS.values())

    def test_new_york_is_largest(self):
        assert CITY_POPULATIONS["new york"] == max(CITY_POPULATIONS.values())

    def test_default_population_is_positive(self):
        assert DEFAULT_POPULATION > 0



class TestComputeRisk:
    def setup_method(self):
        self.f = _fetcher()


    def test_all_zero_inputs_return_zero_overall(self):
        risk = self.f._compute_risk(_make_crime(0), _make_weather(), _make_infra(0), [], "")
        assert risk["overall"] == 0

    def test_all_zero_labels_are_low(self):
        risk = self.f._compute_risk(_make_crime(0), _make_weather(), _make_infra(0), [], "")
        assert risk["overall_label"] == "Low"
        assert risk["crime_label"] == "Low"
        assert risk["weather_label"] == "Low"
        assert risk["infra_label"] == "Low"


    def test_crime_score_chicago_moderate(self):
        risk = self.f._compute_risk(_make_crime(270), _make_weather(), _make_infra(0), [], "chicago")
        assert risk["crime_score"] == 33
        assert risk["crime_label"] == "Moderate"

    def test_crime_score_chicago_high(self):
        risk = self.f._compute_risk(_make_crime(500), _make_weather(), _make_infra(0), [], "chicago")
        assert risk["crime_score"] == 61
        assert risk["crime_label"] == "High"

    def test_crime_score_chicago_capped_at_100(self):
        risk = self.f._compute_risk(_make_crime(10_000), _make_weather(), _make_infra(0), [], "chicago")
        assert risk["crime_score"] == 100
        assert risk["crime_label"] == "Critical"

    def test_crime_score_nyc_lower_than_same_count_in_small_city(self):
        risk_nyc = self.f._compute_risk(_make_crime(200), _make_weather(), _make_infra(0), [], "new york")
        risk_small = self.f._compute_risk(_make_crime(200), _make_weather(), _make_infra(0), [], "")
        assert risk_nyc["crime_score"] < risk_small["crime_score"]

    def test_crime_score_uses_default_pop_for_unknown_city(self):
        risk = self.f._compute_risk(_make_crime(100), _make_weather(), _make_infra(0), [], "unknown_city")
        assert risk["crime_score"] == 66
        assert risk["crime_label"] == "High"


    def test_weather_extreme_alert_scores_100(self):
        weather = _make_weather(alerts=[_make_alert("Extreme")])
        risk = self.f._compute_risk(_make_crime(0), weather, _make_infra(0), [], "")
        assert risk["weather_score"] == 100
        assert risk["weather_label"] == "Critical"

    def test_weather_severe_alert_scores_75(self):
        weather = _make_weather(alerts=[_make_alert("Severe")])
        risk = self.f._compute_risk(_make_crime(0), weather, _make_infra(0), [], "")
        assert risk["weather_score"] == 75
        assert risk["weather_label"] == "Critical"

    def test_weather_moderate_alert_scores_40(self):
        weather = _make_weather(alerts=[_make_alert("Moderate")])
        risk = self.f._compute_risk(_make_crime(0), weather, _make_infra(0), [], "")
        assert risk["weather_score"] == 40
        assert risk["weather_label"] == "Moderate"

    def test_weather_minor_alert_scores_20(self):
        weather = _make_weather(alerts=[_make_alert("Minor")])
        risk = self.f._compute_risk(_make_crime(0), weather, _make_infra(0), [], "")
        assert risk["weather_score"] == 20
        assert risk["weather_label"] == "Low"

    def test_weather_multiple_alerts_uses_max_severity(self):
        weather = _make_weather(alerts=[_make_alert("Moderate"), _make_alert("Severe")])
        risk = self.f._compute_risk(_make_crime(0), weather, _make_infra(0), [], "")
        assert risk["weather_score"] == 75

    def test_weather_unknown_severity_scores_zero(self):
        weather = _make_weather(alerts=[_make_alert("Unknown")])
        risk = self.f._compute_risk(_make_crime(0), weather, _make_infra(0), [], "")
        assert risk["weather_score"] == 0

    def test_weather_no_alerts_high_wind_scores_60(self):
        weather = _make_weather(alerts=[], wind_mph=55)
        risk = self.f._compute_risk(_make_crime(0), weather, _make_infra(0), [], "")
        assert risk["weather_score"] == 60

    def test_weather_no_alerts_moderate_wind_scores_30(self):
        weather = _make_weather(alerts=[], wind_mph=35)
        risk = self.f._compute_risk(_make_crime(0), weather, _make_infra(0), [], "")
        assert risk["weather_score"] == 30

    def test_weather_no_alerts_low_wind_scores_zero(self):
        weather = _make_weather(alerts=[], wind_mph=10)
        risk = self.f._compute_risk(_make_crime(0), weather, _make_infra(0), [], "")
        assert risk["weather_score"] == 0

    def test_weather_alert_present_wind_ignored(self):
        weather = _make_weather(alerts=[_make_alert("Unknown")], wind_mph=60)
        risk = self.f._compute_risk(_make_crime(0), weather, _make_infra(0), [], "")
        assert risk["weather_score"] == 0


    def test_infra_score_chicago_low(self):
        risk = self.f._compute_risk(_make_crime(0), _make_weather(), _make_infra(27), [], "chicago")
        assert risk["infra_score"] == 5
        assert risk["infra_label"] == "Low"

    def test_infra_score_chicago_moderate(self):
        risk = self.f._compute_risk(_make_crime(0), _make_weather(), _make_infra(135), [], "chicago")
        assert risk["infra_score"] == 25
        assert risk["infra_label"] == "Moderate"

    def test_infra_score_capped_at_100(self):
        risk = self.f._compute_risk(_make_crime(0), _make_weather(), _make_infra(100_000), [], "chicago")
        assert risk["infra_score"] == 100


    def test_quake_magnitude_5_scores_70(self):
        quakes = [{"magnitude": 5.0, "place": "", "time": "", "url": ""}]
        risk = self.f._compute_risk(_make_crime(0), _make_weather(), _make_infra(0), quakes, "")
        assert risk["quake_score"] == 70

    def test_quake_magnitude_above_5_still_scores_70(self):
        quakes = [{"magnitude": 7.2, "place": "", "time": "", "url": ""}]
        risk = self.f._compute_risk(_make_crime(0), _make_weather(), _make_infra(0), quakes, "")
        assert risk["quake_score"] == 70

    def test_quake_magnitude_3_scores_30(self):
        quakes = [{"magnitude": 3.0, "place": "", "time": "", "url": ""}]
        risk = self.f._compute_risk(_make_crime(0), _make_weather(), _make_infra(0), quakes, "")
        assert risk["quake_score"] == 30

    def test_quake_magnitude_below_3_scores_zero(self):
        quakes = [{"magnitude": 2.9, "place": "", "time": "", "url": ""}]
        risk = self.f._compute_risk(_make_crime(0), _make_weather(), _make_infra(0), quakes, "")
        assert risk["quake_score"] == 0

    def test_quake_none_magnitude_treated_as_zero(self):
        quakes = [{"magnitude": None, "place": "", "time": "", "url": ""}]
        risk = self.f._compute_risk(_make_crime(0), _make_weather(), _make_infra(0), quakes, "")
        assert risk["quake_score"] == 0

    def test_quake_multiple_uses_max(self):
        quakes = [
            {"magnitude": 3.2, "place": "", "time": "", "url": ""},
            {"magnitude": 5.5, "place": "", "time": "", "url": ""},
        ]
        risk = self.f._compute_risk(_make_crime(0), _make_weather(), _make_infra(0), quakes, "")
        assert risk["quake_score"] == 70

    def test_no_quakes_score_zero(self):
        risk = self.f._compute_risk(_make_crime(0), _make_weather(), _make_infra(0), [], "")
        assert risk["quake_score"] == 0


    def test_overall_uses_weighted_formula(self):
        risk = self.f._compute_risk(
            _make_crime(0),
            _make_weather(),
            _make_infra(0),
            [],
            "",
        )
        assert risk["overall"] == 0

    def test_overall_formula_manual_check(self):
        weather = _make_weather(alerts=[_make_alert("Moderate")])
        quakes = [{"magnitude": 3.2, "place": "", "time": "", "url": ""}]
        risk = self.f._compute_risk(_make_crime(75), weather, _make_infra(25), quakes, "")
        assert risk["overall"] == 40

    def test_overall_max_achievable_value(self):
        weather = _make_weather(alerts=[_make_alert("Extreme")])
        quakes = [{"magnitude": 7.0, "place": "", "time": "", "url": ""}]
        risk = self.f._compute_risk(_make_crime(100_000), weather, _make_infra(100_000), quakes, "")
        assert risk["overall"] == 97

    def test_overall_never_exceeds_100(self):
        weather = _make_weather(alerts=[_make_alert("Extreme")])
        quakes = [{"magnitude": 9.0, "place": "", "time": "", "url": ""}]
        risk = self.f._compute_risk(_make_crime(10_000_000), weather, _make_infra(10_000_000), quakes, "")
        assert 0 <= risk["overall"] <= 100

    def test_result_contains_all_expected_keys(self):
        risk = self.f._compute_risk(_make_crime(0), _make_weather(), _make_infra(0), [], "")
        assert set(risk.keys()) == {
            "overall", "overall_label",
            "crime_score", "crime_label",
            "weather_score", "weather_label",
            "infra_score", "infra_label",
            "quake_score",
        }



class TestWeatherStub:
    def setup_method(self):
        self.f = _fetcher()

    def test_returns_stub_flag(self):
        result = self.f._weather_stub(41.8, -87.6)
        assert result.get("stub") is True

    def test_current_has_required_keys(self):
        current = self.f._weather_stub(0, 0)["current"]
        required = {"temp_f", "feels_like_f", "humidity", "pressure", "wind_mph",
                    "wind_dir", "visibility_mi", "description", "icon", "clouds",
                    "uv_index", "sunrise", "sunset"}
        assert required.issubset(set(current.keys()))

    def test_forecast_is_empty_list(self):
        assert self.f._weather_stub(0, 0)["forecast"] == []

    def test_alerts_is_empty_list(self):
        assert self.f._weather_stub(0, 0)["alerts"] == []



class TestGeocode:
    def setup_method(self):
        self.f = _fetcher()

    @patch("utils.data_fetcher.requests.get")
    def test_returns_correct_lat_lon(self, mock_get, nominatim_response):
        mock_get.return_value = make_ok_response(nominatim_response)
        result = self.f._geocode("Chicago, IL")
        assert result["lat"] == pytest.approx(41.8781, abs=0.001)
        assert result["lon"] == pytest.approx(-87.6298, abs=0.001)

    @patch("utils.data_fetcher.requests.get")
    def test_returns_city_state_zip(self, mock_get, nominatim_response):
        mock_get.return_value = make_ok_response(nominatim_response)
        result = self.f._geocode("Chicago, IL")
        assert result["city"] == "Chicago"
        assert result["state"] == "Illinois"
        assert result["zip"] == "60601"

    @patch("utils.data_fetcher.requests.get")
    def test_empty_results_raises_value_error(self, mock_get):
        mock_get.return_value = make_ok_response([])
        with pytest.raises(ValueError, match="Could not geocode"):
            self.f._geocode("Nonexistent Place XYZ")

    @patch("utils.data_fetcher.requests.get")
    def test_http_error_propagates(self, mock_get):
        mock_get.return_value = make_error_response(500)
        with pytest.raises(requests.HTTPError):
            self.f._geocode("Chicago, IL")

    @patch("utils.data_fetcher.requests.get")
    def test_uses_countrycodes_us(self, mock_get, nominatim_response):
        mock_get.return_value = make_ok_response(nominatim_response)
        self.f._geocode("Chicago, IL")
        _, kwargs = mock_get.call_args
        params = kwargs.get("params", {})
        assert params.get("countrycodes") == "us"

    @patch("utils.data_fetcher.requests.get")
    def test_falls_back_to_town_when_no_city(self, mock_get):
        response = [
            {
                "lat": "42.0",
                "lon": "-71.0",
                "display_name": "Smalltown, MA",
                "address": {
                    "town": "Smalltown",
                    "state": "Massachusetts",
                    "postcode": "02000",
                    "county": "Plymouth County",
                },
            }
        ]
        mock_get.return_value = make_ok_response(response)
        result = self.f._geocode("Smalltown, MA")
        assert result["city"] == "Smalltown"

    @patch("utils.data_fetcher.requests.get")
    def test_falls_back_to_village_when_no_city_or_town(self, mock_get):
        response = [
            {
                "lat": "44.0",
                "lon": "-72.0",
                "display_name": "Tinyville, VT",
                "address": {
                    "village": "Tinyville",
                    "state": "Vermont",
                    "postcode": "05000",
                    "county": "Lamoille County",
                },
            }
        ]
        mock_get.return_value = make_ok_response(response)
        result = self.f._geocode("Tinyville, VT")
        assert result["city"] == "Tinyville"



class TestFetchWeather:
    def setup_method(self):
        self.f = _fetcher()

    def test_returns_stub_when_no_api_key(self):
        with patch("utils.data_fetcher.OPENWEATHER_KEY", ""):
            result = self.f._fetch_weather(41.8, -87.6)
        assert result.get("stub") is True

    @patch("utils.data_fetcher.requests.get")
    def test_parses_current_weather_fields(self, mock_get, owm_current_response, owm_forecast_response):
        mock_get.side_effect = [
            make_ok_response(owm_current_response),
            make_ok_response(owm_forecast_response),
        ]
        with patch("utils.data_fetcher.OPENWEATHER_KEY", "test_key"):
            result = self.f._fetch_weather(41.8, -87.6)

        current = result["current"]
        assert current["temp_f"] == 72
        assert current["feels_like_f"] == 68
        assert current["humidity"] == 55
        assert current["wind_mph"] == 10
        assert current["description"] == "Clear Sky"
        assert current["icon"] == "01d"
        assert current["uv_index"] == 5.2

    @patch("utils.data_fetcher.requests.get")
    def test_visibility_converted_from_meters_to_miles(self, mock_get, owm_current_response, owm_forecast_response):
        mock_get.side_effect = [
            make_ok_response(owm_current_response),
            make_ok_response(owm_forecast_response),
        ]
        with patch("utils.data_fetcher.OPENWEATHER_KEY", "test_key"):
            result = self.f._fetch_weather(41.8, -87.6)
        assert result["current"]["visibility_mi"] == pytest.approx(10.0, abs=0.2)

    @patch("utils.data_fetcher.requests.get")
    def test_forecast_items_parsed_correctly(self, mock_get, owm_current_response, owm_forecast_response):
        mock_get.side_effect = [
            make_ok_response(owm_current_response),
            make_ok_response(owm_forecast_response),
        ]
        with patch("utils.data_fetcher.OPENWEATHER_KEY", "test_key"):
            result = self.f._fetch_weather(41.8, -87.6)

        assert len(result["forecast"]) == 2
        first = result["forecast"][0]
        assert first["dt"] == "2024-01-01 12:00:00"
        assert first["temp_f"] == 70
        assert first["pop"] == 20

    @patch("utils.data_fetcher.requests.get")
    def test_returns_empty_alerts_list(self, mock_get, owm_current_response, owm_forecast_response):
        mock_get.side_effect = [
            make_ok_response(owm_current_response),
            make_ok_response(owm_forecast_response),
        ]
        with patch("utils.data_fetcher.OPENWEATHER_KEY", "test_key"):
            result = self.f._fetch_weather(41.8, -87.6)
        assert result["alerts"] == []

    @patch("utils.data_fetcher.requests.get")
    def test_description_is_title_cased(self, mock_get, owm_current_response, owm_forecast_response):
        mock_get.side_effect = [
            make_ok_response(owm_current_response),
            make_ok_response(owm_forecast_response),
        ]
        with patch("utils.data_fetcher.OPENWEATHER_KEY", "test_key"):
            result = self.f._fetch_weather(41.8, -87.6)
        assert result["current"]["description"] == "Clear Sky"



class TestFetchNwsAlerts:
    def setup_method(self):
        self.f = _fetcher()

    @patch("utils.data_fetcher.requests.get")
    def test_parses_alerts_correctly(self, mock_get, nws_alerts_response):
        mock_get.return_value = make_ok_response(nws_alerts_response)
        result = self.f._fetch_nws_alerts(41.8, -87.6)
        assert len(result) == 2
        assert result[0]["event"] == "Winter Storm Warning"
        assert result[0]["severity"] == "Severe"

    @patch("utils.data_fetcher.requests.get")
    def test_empty_features_returns_empty_list(self, mock_get):
        mock_get.return_value = make_ok_response({"features": []})
        result = self.f._fetch_nws_alerts(41.8, -87.6)
        assert result == []

    @patch("utils.data_fetcher.requests.get")
    def test_http_error_returns_empty_list(self, mock_get):
        mock_get.return_value = make_error_response(503)
        result = self.f._fetch_nws_alerts(41.8, -87.6)
        assert result == []

    @patch("utils.data_fetcher.requests.get")
    def test_caps_at_5_alerts(self, mock_get):
        many_features = {
            "features": [
                {"properties": {
                    "event": f"Event {i}", "severity": "Minor",
                    "headline": "", "description": "", "onset": "", "expires": "",
                }}
                for i in range(10)
            ]
        }
        mock_get.return_value = make_ok_response(many_features)
        result = self.f._fetch_nws_alerts(41.8, -87.6)
        assert len(result) == 5

    @patch("utils.data_fetcher.requests.get")
    def test_description_truncated_at_300_chars(self, mock_get):
        long_desc = "x" * 500
        mock_get.return_value = make_ok_response({
            "features": [{"properties": {
                "event": "Test", "severity": "Minor",
                "headline": "", "description": long_desc, "onset": "", "expires": "",
            }}]
        })
        result = self.f._fetch_nws_alerts(41.8, -87.6)
        assert len(result[0]["description"]) == 300

    @patch("utils.data_fetcher.requests.get")
    def test_logs_warning_on_error(self, mock_get):
        mock_get.side_effect = ConnectionError("timeout")
        with patch("utils.data_fetcher.logger") as mock_logger:
            result = self.f._fetch_nws_alerts(41.8, -87.6)
        assert result == []
        mock_logger.warning.assert_called_once()



class TestFetchFbiStats:
    def setup_method(self):
        self.f = _fetcher()

    def test_no_api_key_returns_note(self):
        with patch("utils.data_fetcher.FBI_API_KEY", ""):
            result = self.f._fetch_fbi_stats("Illinois")
        assert "note" in result

    def test_unknown_state_returns_note(self):
        with patch("utils.data_fetcher.FBI_API_KEY", "test_key"):
            result = self.f._fetch_fbi_stats("Narnia")
        assert "note" in result

    def test_empty_state_returns_note(self):
        with patch("utils.data_fetcher.FBI_API_KEY", "test_key"):
            result = self.f._fetch_fbi_stats("")
        assert "note" in result

    @patch("utils.data_fetcher.requests.get")
    def test_uses_correct_state_abbreviation_in_url(self, mock_get):
        mock_get.return_value = make_ok_response({"data": []})
        with patch("utils.data_fetcher.FBI_API_KEY", "test_key"):
            self.f._fetch_fbi_stats("California")
        call_args = mock_get.call_args
        url = call_args[0][0]
        assert "/CA/" in url

    @patch("utils.data_fetcher.requests.get")
    def test_illinois_uses_il_abbreviation(self, mock_get):
        mock_get.return_value = make_ok_response({"data": []})
        with patch("utils.data_fetcher.FBI_API_KEY", "test_key"):
            self.f._fetch_fbi_stats("Illinois")
        url = mock_get.call_args[0][0]
        assert "/IL/" in url

    @patch("utils.data_fetcher.requests.get")
    def test_http_error_returns_note_and_logs_warning(self, mock_get):
        mock_get.return_value = make_error_response(500)
        with patch("utils.data_fetcher.FBI_API_KEY", "test_key"), \
             patch("utils.data_fetcher.logger") as mock_logger:
            result = self.f._fetch_fbi_stats("Texas")
        assert "note" in result
        mock_logger.warning.assert_called_once()

    @patch("utils.data_fetcher.requests.get")
    def test_successful_response_returned_as_is(self, mock_get):
        api_data = {"data": [{"year": 2022, "violent_crime": 1234}]}
        mock_get.return_value = make_ok_response(api_data)
        with patch("utils.data_fetcher.FBI_API_KEY", "test_key"):
            result = self.f._fetch_fbi_stats("Texas")
        assert result == api_data



class TestFbiAgencyHelpers:
    def test_haversine_zero(self):
        assert DataFetcher._haversine_km(41.0, -87.0, 41.0, -87.0) == 0

    def test_haversine_chicago_to_nyc(self):
        d = DataFetcher._haversine_km(41.88, -87.63, 40.71, -74.00)
        assert 1100 < d < 1300

    def test_normalize_from_list(self):
        data = [{"ori": "A"}, {"ori": "B"}, "junk"]
        assert DataFetcher._normalize_agency_list(data) == [{"ori": "A"}, {"ori": "B"}]

    def test_normalize_from_dict_keyed_by_ori(self):
        data = {"IL0010000": {"agency_name": "X"}, "IL0020000": {"agency_name": "Y", "ori": "Z"}}
        out = DataFetcher._normalize_agency_list(data)
        assert sorted(a["ori"] for a in out) == ["IL0010000", "Z"]

    def test_normalize_from_agencies_field(self):
        assert DataFetcher._normalize_agency_list({"agencies": [{"ori": "A"}]}) == [{"ori": "A"}]

    def test_cde_latest_offenses_actuals_ignores_national(self):
        payload = {"offenses": {"actuals": {
            "United States Total": {"2021": 1000000, "2022": 1100000},
            "Springfield Police Department": {"2020": 100, "2021": 150, "2022": 175},
        }}}
        assert DataFetcher._cde_latest_total(payload) == (2022, 175)

    def test_cde_latest_list_shape(self):
        payload = [{"data_year": 2020, "actual": 10}, {"data_year": 2022, "actual": 30}]
        assert DataFetcher._cde_latest_total(payload) == (2022, 30)

    def test_cde_latest_year_dict_shape(self):
        assert DataFetcher._cde_latest_total({"2019": 5, "2023": 9}) == (2023, 9)

    def test_cde_latest_empty(self):
        assert DataFetcher._cde_latest_total({}) is None
        assert DataFetcher._cde_latest_total({"offenses": {"actuals": {}}}) is None



class TestFetchFbiAgency:
    def setup_method(self):
        self.f = _fetcher()

    def test_no_key_returns_empty(self):
        with patch("utils.data_fetcher.FBI_API_KEY", ""):
            assert self.f._fetch_fbi_agency(41.88, -87.63, "Illinois") == {}

    def test_unknown_state_returns_empty(self):
        with patch("utils.data_fetcher.FBI_API_KEY", "k"):
            assert self.f._fetch_fbi_agency(41.88, -87.63, "Narnia") == {}

    @patch("utils.data_fetcher.requests.get")
    def test_nearest_agency_and_offense_totals(self, mock_get):
        agencies = [
            {"ori": "IL0010000", "agency_name": "Far PD", "latitude": "10.0", "longitude": "10.0"},
            {"ori": "IL0020000", "agency_name": "Near PD", "county_name": "Cook",
             "latitude": "41.88", "longitude": "-87.63"},
        ]
        violent = {"offenses": {"actuals": {"Near PD": {"2021": 100, "2022": 120}}}}
        prop = {"offenses": {"actuals": {"Near PD": {"2021": 400, "2022": 450}}}}
        mock_get.side_effect = [
            make_ok_response(agencies),
            make_ok_response(violent),
            make_ok_response(prop),
        ]
        with patch("utils.data_fetcher.FBI_API_KEY", "k"):
            out = self.f._fetch_fbi_agency(41.88, -87.63, "Illinois", "Chicago", "Cook County")
        assert out["ori"] == "IL0020000"
        assert out["agency_name"] == "Near PD"
        assert out["violent_crime"] == 120 and out["violent_year"] == 2022
        assert out["property_crime"] == 450 and out["property_year"] == 2022

    @patch("utils.data_fetcher.requests.get")
    def test_name_fallback_when_no_coords(self, mock_get):
        agencies = [
            {"ori": "IL0010000", "agency_name": "Aurora Police Department"},
            {"ori": "IL0020000", "agency_name": "Springfield Police Department"},
        ]
        offense = {"offenses": {"actuals": {"Springfield": {"2022": 50}}}}
        mock_get.side_effect = [
            make_ok_response(agencies),
            make_ok_response(offense),
            make_ok_response({}),
        ]
        with patch("utils.data_fetcher.FBI_API_KEY", "k"):
            out = self.f._fetch_fbi_agency(39.8, -89.6, "Illinois", "Springfield", "Sangamon County")
        assert out["ori"] == "IL0020000"
        assert out["violent_crime"] == 50
        assert "property_crime" not in out

    @patch("utils.data_fetcher.requests.get")
    def test_returns_empty_when_no_totals(self, mock_get):
        agencies = [{"ori": "IL0010000", "agency_name": "X", "latitude": "41.0", "longitude": "-87.0"}]
        mock_get.side_effect = [
            make_ok_response(agencies),
            make_ok_response({}),
            make_ok_response({}),
        ]
        with patch("utils.data_fetcher.FBI_API_KEY", "k"):
            assert self.f._fetch_fbi_agency(41.0, -87.0, "Illinois") == {}

    @patch.object(DataFetcher, "_fetch_fbi_agency")
    @patch.object(DataFetcher, "_fetch_fbi_stats")
    @patch.object(DataFetcher, "_fetch_socrata_crime")
    def test_crime_includes_summary_when_no_incidents(self, mock_socrata, mock_stats, mock_agency):
        mock_socrata.return_value = []
        mock_stats.return_value = {}
        mock_agency.return_value = {"agency_name": "Near PD", "violent_crime": 120}
        result = self.f._fetch_crime(
            39.8, -89.6, "", state="Illinois",
            geo={"city": "Springfield", "county": "Sangamon County"},
        )
        assert result["fbi_summary"]["violent_crime"] == 120
        mock_agency.assert_called_once()

    @patch.object(DataFetcher, "_fetch_fbi_agency")
    @patch.object(DataFetcher, "_fetch_fbi_stats")
    @patch.object(DataFetcher, "_fetch_socrata_crime")
    def test_crime_skips_summary_when_incidents_present(self, mock_socrata, mock_stats, mock_agency):
        mock_stats.return_value = {}
        mock_socrata.return_value = [
            {"type": "THEFT", "description": "", "date": "", "location": "", "block": "", "lat": 0, "lon": 0}
        ]
        result = self.f._fetch_crime(41.88, -87.63, "chicago", state="Illinois", geo={"city": "Chicago"})
        assert result["fbi_summary"] == {}
        mock_agency.assert_not_called()



class TestFetchSocrataCrime:
    def setup_method(self):
        self.f = _fetcher()

    @patch("utils.data_fetcher.requests.get")
    def test_chicago_query_uses_primary_type_field(self, mock_get):
        rows = [{"primary_type": "THEFT", "description": "RETAIL THEFT",
                 "date": "2024-01-15", "location_description": "STORE",
                 "latitude": "41.88", "longitude": "-87.63", "block": "001XX N STATE"}]
        mock_get.return_value = make_ok_response(rows)
        result = self.f._fetch_socrata_crime(41.88, -87.63, "chicago")
        assert result[0]["type"] == "Theft & Burglary"

    @patch("utils.data_fetcher.requests.get")
    def test_new_york_query_uses_ofns_desc_field(self, mock_get):
        rows = [{"ofns_desc": "ROBBERY", "law_cat_cd": "FELONY",
                 "cmplnt_fr_dt": "2024-01-15", "boro_nm": "BRONX",
                 "latitude": "40.85", "longitude": "-73.86"}]
        mock_get.return_value = make_ok_response(rows)
        result = self.f._fetch_socrata_crime(40.85, -73.86, "new york")
        assert result[0]["type"] == "Theft & Burglary"

    @patch("utils.data_fetcher.requests.get")
    def test_unknown_type_falls_back_to_unknown(self, mock_get):
        rows = [{"some_other_field": "data", "latitude": "41.88", "longitude": "-87.63"}]
        mock_get.return_value = make_ok_response(rows)
        result = self.f._fetch_socrata_crime(41.88, -87.63, "chicago")
        assert result[0]["type"] == "Other/Unknown"

    @patch("utils.data_fetcher.requests.get")
    def test_http_error_returns_empty_list(self, mock_get):
        mock_get.return_value = make_error_response(429)
        result = self.f._fetch_socrata_crime(41.88, -87.63, "chicago")
        assert result == []

    @patch("utils.data_fetcher.requests.get")
    def test_logs_warning_on_http_error(self, mock_get):
        mock_get.return_value = make_error_response(500)
        with patch("utils.data_fetcher.logger") as mock_logger:
            self.f._fetch_socrata_crime(41.88, -87.63, "chicago")
        mock_logger.warning.assert_called_once()

    @patch("utils.data_fetcher.requests.get")
    def test_invalid_lat_lon_falls_back_to_query_coords(self, mock_get):
        rows = [{"primary_type": "THEFT", "latitude": "not_a_number", "longitude": ""}]
        mock_get.return_value = make_ok_response(rows)
        result = self.f._fetch_socrata_crime(41.88, -87.63, "chicago")
        assert result[0]["lat"] == 41.88
        assert result[0]["lon"] == -87.63

    @patch("utils.data_fetcher.requests.get")
    def test_missing_lat_lon_falls_back_to_query_coords(self, mock_get):
        rows = [{"primary_type": "THEFT"}]
        mock_get.return_value = make_ok_response(rows)
        result = self.f._fetch_socrata_crime(41.88, -87.63, "chicago")
        assert result[0]["lat"] == 41.88
        assert result[0]["lon"] == -87.63

    @patch("utils.data_fetcher.requests.get")
    def test_adds_socrata_token_header_when_set(self, mock_get):
        mock_get.return_value = make_ok_response([])
        with patch("utils.data_fetcher.SOCRATA_TOKEN", "test_token"):
            self.f._fetch_socrata_crime(41.88, -87.63, "chicago")
        headers = mock_get.call_args[1].get("headers", {})
        assert headers.get("X-App-Token") == "test_token"

    @patch("utils.data_fetcher.requests.get")
    def test_no_socrata_token_sends_empty_headers(self, mock_get):
        mock_get.return_value = make_ok_response([])
        with patch("utils.data_fetcher.SOCRATA_TOKEN", ""):
            self.f._fetch_socrata_crime(41.88, -87.63, "chicago")
        headers = mock_get.call_args[1].get("headers", {})
        assert "X-App-Token" not in headers



class TestFetch311City:
    def setup_method(self):
        self.f = _fetcher()

    @patch("utils.data_fetcher.requests.get")
    def test_parses_chicago_fields(self, mock_get):
        rows = [{"type_of_service_request": "Pothole in Street",
                 "status": "Open", "creation_date": "2024-01-15",
                 "street_address": "100 N STATE ST"}]
        mock_get.return_value = make_ok_response(rows)
        result = self.f._fetch_311_city(41.88, -87.63, "chicago")
        assert result[0]["category"] == "Pothole in Street"
        assert result[0]["status"] == "Open"

    @patch("utils.data_fetcher.requests.get")
    def test_parses_new_york_fields(self, mock_get):
        rows = [{"complaint_type": "Noise - Residential",
                 "status": "Closed", "created_date": "2024-01-14",
                 "incident_address": "50 BROADWAY"}]
        mock_get.return_value = make_ok_response(rows)
        result = self.f._fetch_311_city(40.70, -74.01, "new york")
        assert result[0]["category"] == "Noise - Residential"

    @patch("utils.data_fetcher.requests.get")
    def test_http_error_returns_empty_list(self, mock_get):
        mock_get.return_value = make_error_response(500)
        result = self.f._fetch_311_city(41.88, -87.63, "chicago")
        assert result == []

    @patch("utils.data_fetcher.requests.get")
    def test_logs_warning_on_http_error(self, mock_get):
        mock_get.return_value = make_error_response(500)
        with patch("utils.data_fetcher.logger") as mock_logger:
            self.f._fetch_311_city(41.88, -87.63, "chicago")
        mock_logger.warning.assert_called_once()

    @patch("utils.data_fetcher.requests.get")
    def test_category_falls_back_to_other(self, mock_get):
        rows = [{"unrecognized_field": "value"}]
        mock_get.return_value = make_ok_response(rows)
        result = self.f._fetch_311_city(41.88, -87.63, "chicago")
        assert result[0]["category"] == "Other"

    @patch("utils.data_fetcher.requests.get")
    def test_status_falls_back_to_open(self, mock_get):
        rows = [{"type_of_service_request": "Pothole"}]
        mock_get.return_value = make_ok_response(rows)
        result = self.f._fetch_311_city(41.88, -87.63, "chicago")
        assert result[0]["status"] == "Open"



class TestFetch311:
    def setup_method(self):
        self.f = _fetcher()

    def test_unsupported_city_returns_empty(self):
        result = self.f._fetch_311(41.88, -87.63, "unsupported_city")
        assert result["total"] == 0
        assert result["complaints"] == []
        assert result["categories"] == {}

    def test_empty_city_key_returns_empty(self):
        result = self.f._fetch_311(41.88, -87.63, "")
        assert result["total"] == 0

    @patch.object(DataFetcher, "_fetch_311_city")
    def test_categories_built_from_complaints(self, mock_fetch):
        mock_fetch.return_value = [
            {"category": "Pothole", "status": "Open", "date": "", "address": ""},
            {"category": "Pothole", "status": "Open", "date": "", "address": ""},
            {"category": "Noise", "status": "Closed", "date": "", "address": ""},
        ]
        result = self.f._fetch_311(41.88, -87.63, "chicago")
        assert result["total"] == 3
        assert result["categories"]["Pothole"] == 2
        assert result["categories"]["Noise"] == 1

    @patch.object(DataFetcher, "_fetch_311_city")
    def test_complaints_capped_at_100(self, mock_fetch):
        mock_fetch.return_value = [
            {"category": "Other", "status": "Open", "date": "", "address": ""}
            for _ in range(200)
        ]
        result = self.f._fetch_311(41.88, -87.63, "chicago")
        assert len(result["complaints"]) == 100
        assert result["total"] == 200



class TestFetchEarthquakes:
    def setup_method(self):
        self.f = _fetcher()

    @patch("utils.data_fetcher.requests.get")
    def test_parses_quake_fields(self, mock_get, usgs_response):
        mock_get.return_value = make_ok_response(usgs_response)
        result = self.f._fetch_earthquakes(37.3, -121.9)
        assert result[0]["magnitude"] == 3.2
        assert result[0]["place"] == "15km N of San Jose, CA"
        assert "url" in result[0]
        assert "time" in result[0]

    @patch("utils.data_fetcher.requests.get")
    def test_empty_features_returns_empty_list(self, mock_get):
        mock_get.return_value = make_ok_response({"features": []})
        result = self.f._fetch_earthquakes(37.3, -121.9)
        assert result == []

    @patch("utils.data_fetcher.requests.get")
    def test_http_error_returns_empty_list(self, mock_get):
        mock_get.return_value = make_error_response(500)
        result = self.f._fetch_earthquakes(37.3, -121.9)
        assert result == []

    @patch("utils.data_fetcher.requests.get")
    def test_logs_warning_on_error(self, mock_get):
        mock_get.side_effect = ConnectionError("timeout")
        with patch("utils.data_fetcher.logger") as mock_logger:
            result = self.f._fetch_earthquakes(37.3, -121.9)
        assert result == []
        mock_logger.warning.assert_called_once()

    @patch("utils.data_fetcher.requests.get")
    def test_time_is_formatted_string_not_epoch(self, mock_get, usgs_response):
        mock_get.return_value = make_ok_response(usgs_response)
        result = self.f._fetch_earthquakes(37.3, -121.9)
        assert isinstance(result[0]["time"], str)
        assert "UTC" in result[0]["time"]

    @patch("utils.data_fetcher.requests.get")
    def test_request_includes_correct_params(self, mock_get):
        mock_get.return_value = make_ok_response({"features": []})
        self.f._fetch_earthquakes(37.3, -121.9)
        params = mock_get.call_args[1].get("params", {})
        assert params["format"] == "geojson"
        assert params["maxradiuskm"] == 500
        assert params["minmagnitude"] == 2.0



class TestFetchCrime:
    def setup_method(self):
        self.f = _fetcher()

    @patch.object(DataFetcher, "_fetch_socrata_crime")
    @patch.object(DataFetcher, "_fetch_fbi_stats")
    def test_supported_city_calls_socrata(self, mock_fbi, mock_socrata):
        mock_socrata.return_value = []
        mock_fbi.return_value = {}
        self.f._fetch_crime(41.88, -87.63, "chicago", state="Illinois")
        mock_socrata.assert_called_once_with(41.88, -87.63, "chicago")

    @patch.object(DataFetcher, "_fetch_socrata_crime")
    @patch.object(DataFetcher, "_fetch_fbi_stats")
    def test_unsupported_city_skips_socrata(self, mock_fbi, mock_socrata):
        mock_fbi.return_value = {}
        self.f._fetch_crime(41.88, -87.63, "", state="Illinois")
        mock_socrata.assert_not_called()

    @patch.object(DataFetcher, "_fetch_fbi_stats")
    @patch.object(DataFetcher, "_fetch_socrata_crime")
    def test_fbi_called_with_state_name(self, mock_socrata, mock_fbi):
        mock_socrata.return_value = []
        mock_fbi.return_value = {}
        self.f._fetch_crime(41.88, -87.63, "chicago", state="Illinois")
        mock_fbi.assert_called_once_with("Illinois")

    @patch.object(DataFetcher, "_fetch_socrata_crime")
    @patch.object(DataFetcher, "_fetch_fbi_stats")
    def test_type_counts_aggregated_correctly(self, mock_fbi, mock_socrata):
        mock_fbi.return_value = {}
        mock_socrata.return_value = [
            {"type": "THEFT", "description": "", "date": "", "location": "", "block": "", "lat": 0, "lon": 0},
            {"type": "THEFT", "description": "", "date": "", "location": "", "block": "", "lat": 0, "lon": 0},
            {"type": "BATTERY", "description": "", "date": "", "location": "", "block": "", "lat": 0, "lon": 0},
        ]
        result = self.f._fetch_crime(41.88, -87.63, "chicago", state="Illinois")
        assert result["type_counts"]["THEFT"] == 2
        assert result["type_counts"]["BATTERY"] == 1
        assert result["total_count"] == 3

    @patch.object(DataFetcher, "_fetch_socrata_crime")
    @patch.object(DataFetcher, "_fetch_fbi_stats")
    def test_incidents_capped_at_200(self, mock_fbi, mock_socrata):
        mock_fbi.return_value = {}
        mock_socrata.return_value = [
            {"type": "THEFT", "description": "", "date": "", "location": "", "block": "", "lat": 0, "lon": 0}
            for _ in range(300)
        ]
        result = self.f._fetch_crime(41.88, -87.63, "chicago", state="Illinois")
        assert len(result["incidents"]) == 200
        assert result["total_count"] == 300



class TestFetchAll:
    def setup_method(self):
        self.f = _fetcher()

    @patch.object(DataFetcher, "_geocode")
    @patch.object(DataFetcher, "_fetch_weather")
    @patch.object(DataFetcher, "_fetch_nws_alerts")
    @patch.object(DataFetcher, "_fetch_crime")
    @patch.object(DataFetcher, "_fetch_311")
    @patch.object(DataFetcher, "_fetch_earthquakes")
    def test_returns_all_top_level_keys(
        self, mock_quakes, mock_311, mock_crime, mock_nws, mock_weather, mock_geo,
        geo_chicago, weather_clear, crime_empty, infra_empty
    ):
        mock_geo.return_value = geo_chicago
        mock_weather.return_value = weather_clear
        mock_nws.return_value = []
        mock_crime.return_value = crime_empty
        mock_311.return_value = infra_empty
        mock_quakes.return_value = []

        result = self.f.fetch_all("Chicago, IL")

        assert set(result.keys()) == {"geo", "weather", "crime", "infrastructure",
                                       "earthquakes", "risk_score", "fetched_at"}

    @patch.object(DataFetcher, "_geocode")
    @patch.object(DataFetcher, "_fetch_weather")
    @patch.object(DataFetcher, "_fetch_nws_alerts")
    @patch.object(DataFetcher, "_fetch_crime")
    @patch.object(DataFetcher, "_fetch_311")
    @patch.object(DataFetcher, "_fetch_earthquakes")
    def test_nws_alerts_merged_into_weather(
        self, mock_quakes, mock_311, mock_crime, mock_nws, mock_weather, mock_geo,
        geo_chicago, weather_clear, crime_empty, infra_empty
    ):
        mock_geo.return_value = geo_chicago
        mock_weather.return_value = dict(weather_clear)
        mock_nws.return_value = [{"event": "Test Alert", "severity": "Moderate"}]
        mock_crime.return_value = crime_empty
        mock_311.return_value = infra_empty
        mock_quakes.return_value = []

        result = self.f.fetch_all("Chicago, IL")
        assert result["weather"]["alerts"] == [{"event": "Test Alert", "severity": "Moderate"}]

    @patch.object(DataFetcher, "_geocode")
    @patch.object(DataFetcher, "_fetch_weather")
    @patch.object(DataFetcher, "_fetch_nws_alerts")
    @patch.object(DataFetcher, "_fetch_crime")
    @patch.object(DataFetcher, "_fetch_311")
    @patch.object(DataFetcher, "_fetch_earthquakes")
    def test_fetched_at_is_utc_iso_format(
        self, mock_quakes, mock_311, mock_crime, mock_nws, mock_weather, mock_geo,
        geo_chicago, weather_clear, crime_empty, infra_empty
    ):
        mock_geo.return_value = geo_chicago
        mock_weather.return_value = weather_clear
        mock_nws.return_value = []
        mock_crime.return_value = crime_empty
        mock_311.return_value = infra_empty
        mock_quakes.return_value = []

        result = self.f.fetch_all("Chicago, IL")
        assert result["fetched_at"].endswith("Z")

    @patch.object(DataFetcher, "_geocode")
    @patch.object(DataFetcher, "_fetch_weather")
    @patch.object(DataFetcher, "_fetch_nws_alerts")
    @patch.object(DataFetcher, "_fetch_crime")
    @patch.object(DataFetcher, "_fetch_311")
    @patch.object(DataFetcher, "_fetch_earthquakes")
    def test_city_key_passed_to_crime_and_311(
        self, mock_quakes, mock_311, mock_crime, mock_nws, mock_weather, mock_geo,
        geo_chicago, weather_clear, crime_empty, infra_empty
    ):
        mock_geo.return_value = geo_chicago
        mock_weather.return_value = weather_clear
        mock_nws.return_value = []
        mock_crime.return_value = crime_empty
        mock_311.return_value = infra_empty
        mock_quakes.return_value = []

        self.f.fetch_all("Chicago, IL")

        crime_call = mock_crime.call_args
        assert crime_call[0][2] == "chicago"

        infra_call = mock_311.call_args
        assert infra_call[0][2] == "chicago"

    @patch.object(DataFetcher, "_geocode")
    def test_geocode_error_propagates(self, mock_geo):
        mock_geo.side_effect = ValueError("Could not geocode: xyz")
        with pytest.raises(ValueError, match="Could not geocode"):
            self.f.fetch_all("xyz")
