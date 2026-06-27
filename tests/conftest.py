"""
Shared pytest fixtures for NeighborhoodAlert tests.
"""

import pytest
from unittest.mock import MagicMock
import requests



def make_ok_response(json_data):
    """Return a mock requests.Response that succeeds with json_data."""
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = 200
    mock.raise_for_status.return_value = None
    return mock


def make_error_response(status_code=500):
    """Return a mock requests.Response that raises HTTPError."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.raise_for_status.side_effect = requests.HTTPError(
        f"HTTP {status_code} Error"
    )
    return mock



@pytest.fixture
def geo_chicago():
    return {
        "lat": 41.8781,
        "lon": -87.6298,
        "display_name": "Chicago, Cook County, Illinois, United States",
        "city": "Chicago",
        "state": "Illinois",
        "zip": "60601",
        "county": "Cook County",
    }


@pytest.fixture
def geo_unknown():
    return {
        "lat": 39.5,
        "lon": -98.35,
        "display_name": "Geographic Center of the United States",
        "city": "Lebanon",
        "state": "Kansas",
        "zip": "66952",
        "county": "Smith County",
    }


@pytest.fixture
def weather_clear():
    return {
        "current": {
            "temp_f": 72,
            "feels_like_f": 70,
            "humidity": 55,
            "pressure": 1013,
            "wind_mph": 8,
            "wind_dir": 180,
            "visibility_mi": 10.0,
            "description": "Clear Sky",
            "icon": "01d",
            "clouds": 0,
            "uv_index": None,
            "sunrise": "06:30 AM",
            "sunset": "07:45 PM",
        },
        "forecast": [],
        "alerts": [],
    }


@pytest.fixture
def weather_severe():
    return {
        "current": {
            "temp_f": 45,
            "feels_like_f": 38,
            "humidity": 80,
            "pressure": 995,
            "wind_mph": 55,
            "wind_dir": 270,
            "visibility_mi": 2.0,
            "description": "Heavy Rain",
            "icon": "10d",
            "clouds": 100,
            "uv_index": None,
            "sunrise": "06:30 AM",
            "sunset": "07:45 PM",
        },
        "forecast": [],
        "alerts": [
            {
                "event": "Tornado Warning",
                "severity": "Extreme",
                "headline": "Tornado Warning in effect",
                "description": "A tornado warning is in effect.",
                "onset": "2024-01-01T12:00:00Z",
                "expires": "2024-01-01T14:00:00Z",
            }
        ],
    }


@pytest.fixture
def crime_empty():
    return {
        "incidents": [],
        "total_count": 0,
        "type_counts": {},
        "fbi_stats": {},
        "period_days": 30,
    }


@pytest.fixture
def crime_chicago(geo_chicago):
    incidents = [
        {"type": "THEFT", "description": "POCKET-PICKING", "date": "2024-01-15",
         "location": "STREET", "block": "001XX N STATE ST", "lat": 41.88, "lon": -87.63},
        {"type": "BATTERY", "description": "SIMPLE", "date": "2024-01-14",
         "location": "RESIDENCE", "block": "002XX W MADISON ST", "lat": 41.88, "lon": -87.64},
        {"type": "THEFT", "description": "FROM BUILDING", "date": "2024-01-13",
         "location": "APARTMENT", "block": "003XX S MICHIGAN AVE", "lat": 41.88, "lon": -87.62},
    ]
    return {
        "incidents": incidents,
        "total_count": len(incidents),
        "type_counts": {"THEFT": 2, "BATTERY": 1},
        "fbi_stats": {},
        "period_days": 30,
    }


@pytest.fixture
def infra_empty():
    return {"complaints": [], "total": 0, "categories": {}}


@pytest.fixture
def infra_chicago():
    complaints = [
        {"category": "Pothole in Street", "status": "Open",
         "date": "2024-01-15", "address": "100 N STATE ST"},
        {"category": "Street Light Out", "status": "Open",
         "date": "2024-01-14", "address": "200 W MADISON ST"},
    ]
    return {
        "complaints": complaints,
        "total": len(complaints),
        "categories": {"Pothole in Street": 1, "Street Light Out": 1},
    }


@pytest.fixture
def quakes_empty():
    return []


@pytest.fixture
def quakes_moderate():
    return [
        {"magnitude": 3.2, "place": "15km N of San Jose, CA",
         "time": "2024-01-10 08:30 UTC", "url": "https://earthquake.usgs.gov/eq/1"},
    ]


@pytest.fixture
def quakes_major():
    return [
        {"magnitude": 5.8, "place": "20km E of Los Angeles, CA",
         "time": "2024-01-10 08:30 UTC", "url": "https://earthquake.usgs.gov/eq/2"},
    ]


@pytest.fixture
def full_data(geo_chicago, weather_clear, crime_chicago, infra_chicago, quakes_empty):
    return {
        "geo": geo_chicago,
        "weather": weather_clear,
        "crime": crime_chicago,
        "infrastructure": infra_chicago,
        "earthquakes": quakes_empty,
        "risk_score": {
            "overall": 10,
            "overall_label": "Low",
            "crime_score": 10,
            "crime_label": "Low",
            "weather_score": 0,
            "weather_label": "Low",
            "infra_score": 0,
            "infra_label": "Low",
            "quake_score": 0,
        },
        "fetched_at": "2024-01-15T12:00:00Z",
    }



@pytest.fixture
def owm_current_response():
    return {
        "main": {
            "temp": 72.0,
            "feels_like": 68.0,
            "humidity": 55,
            "pressure": 1013,
        },
        "wind": {"speed": 10.0, "deg": 180},
        "visibility": 16090,
        "weather": [{"description": "clear sky", "icon": "01d"}],
        "clouds": {"all": 0},
        "uvi": 5.2,
        "sys": {"sunrise": 1700000000, "sunset": 1700040000},
    }


@pytest.fixture
def owm_forecast_response():
    return {
        "list": [
            {
                "dt_txt": "2024-01-01 12:00:00",
                "main": {"temp": 70.0, "humidity": 50},
                "weather": [{"description": "few clouds"}],
                "wind": {"speed": 5.0},
                "pop": 0.2,
            },
            {
                "dt_txt": "2024-01-01 15:00:00",
                "main": {"temp": 68.0, "humidity": 60},
                "weather": [{"description": "overcast clouds"}],
                "wind": {"speed": 8.0},
                "pop": 0.5,
            },
        ]
    }


@pytest.fixture
def nominatim_response():
    return [
        {
            "lat": "41.8781",
            "lon": "-87.6298",
            "display_name": "Chicago, Cook County, Illinois, United States",
            "address": {
                "city": "Chicago",
                "state": "Illinois",
                "postcode": "60601",
                "county": "Cook County",
            },
        }
    ]


@pytest.fixture
def nws_alerts_response():
    return {
        "features": [
            {
                "properties": {
                    "event": "Winter Storm Warning",
                    "severity": "Severe",
                    "headline": "Winter Storm Warning in effect until Monday",
                    "description": "Heavy snow expected. Total accumulations of 8-12 inches.",
                    "onset": "2024-01-15T18:00:00Z",
                    "expires": "2024-01-16T18:00:00Z",
                }
            },
            {
                "properties": {
                    "event": "Wind Advisory",
                    "severity": "Moderate",
                    "headline": "Wind Advisory in effect",
                    "description": "Southwest winds 25-35 mph.",
                    "onset": "2024-01-15T12:00:00Z",
                    "expires": "2024-01-15T21:00:00Z",
                }
            },
        ]
    }


@pytest.fixture
def usgs_response():
    return {
        "features": [
            {
                "properties": {
                    "mag": 3.2,
                    "place": "15km N of San Jose, CA",
                    "time": 1704844200000,
                    "url": "https://earthquake.usgs.gov/earthquakes/eventpage/nc1",
                }
            },
            {
                "properties": {
                    "mag": 2.1,
                    "place": "5km S of Gilroy, CA",
                    "time": 1704830000000,
                    "url": "https://earthquake.usgs.gov/earthquakes/eventpage/nc2",
                }
            },
        ]
    }
