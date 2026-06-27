"""
DataFetcher — pulls from all real-time public data sources:
  • OpenWeatherMap (current + forecast + NWS alerts)
  • Socrata Open Data API (city crime incidents)
  • FBI Crime Data Explorer (national crime stats)
  • 311 Open Data (infrastructure complaints)
  • Nominatim (free geocoding, no API key required)
  • USGS Earthquake feed
  • NWS Alerts (weather.gov)
"""

import os
import math
import logging
import time
import requests
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, List

logger = logging.getLogger(__name__)

OPENWEATHER_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
FBI_API_KEY     = os.environ.get("FBI_CRIME_API_KEY", "")

SOCRATA_TOKEN = os.environ.get("SOCRATA_APP_TOKEN", "")

FBI_CDE_BASE = "https://api.usa.gov/crime/fbi/cde"

SOCRATA_ENDPOINTS = {
    "chicago": "https://data.cityofchicago.org/resource/ijzp-q8t2.json",
    "new york": "https://data.cityofnewyork.us/resource/5uac-w243.json",
    "los angeles": "https://data.lacity.org/resource/2nrs-mtv8.json",
    "san francisco": "https://data.sfgov.org/resource/wg3w-h783.json",
    "seattle": "https://data.seattle.gov/resource/tazs-3rd5.json",
    "dallas": "https://www.dallasopendata.com/resource/qv6i-rri7.json",
    "austin": "https://data.austintexas.gov/resource/fdj4-gpfu.json",
    "denver": "https://data.denvergov.org/resource/mnz9-vjy7.json",
    "houston": "https://data.houstontx.gov/resource/kubn-qncu.json",
    "boston": "https://data.boston.gov/resource/crime.json",
}

CITY_311_ENDPOINTS = {
    "chicago": "https://data.cityofchicago.org/resource/v6vf-nfxy.json",
    "new york": "https://data.cityofnewyork.us/resource/erm2-nwe9.json",
    "san francisco": "https://data.sfgov.org/resource/vw6y-z8j6.json",
    "los angeles": "https://data.lacity.org/resource/rq3b-xjk8.json",
    "seattle": "https://data.seattle.gov/resource/55dj-4iis.json",
    "boston": "https://data.boston.gov/resource/wc8w-nujj.json",
}

HEADERS = {"User-Agent": "NeighborhoodAlert/1.0 (contact@neighborhoodalert.app)"}

CITY_POPULATIONS = {
    "chicago":       2_700_000,
    "new york":      8_300_000,
    "los angeles":   3_900_000,
    "san francisco":   870_000,
    "seattle":         750_000,
    "dallas":        1_300_000,
    "austin":          980_000,
    "denver":          720_000,
    "houston":       2_300_000,
    "boston":          670_000,
}
DEFAULT_POPULATION = 500_000

STATE_ABBREVS = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
}


class DataFetcher:

    @staticmethod
    def _safe_get(url: str, *, retries: int = 1, **kwargs) -> requests.Response:
        """GET with a single retry on 5xx / connection errors."""
        kwargs.setdefault("timeout", 10)
        for attempt in range(1 + retries):
            try:
                r = requests.get(url, **kwargs)
                if r.status_code >= 500 and attempt < retries:
                    time.sleep(1)
                    continue
                return r
            except (requests.ConnectionError, requests.Timeout):
                if attempt < retries:
                    time.sleep(1)
                    continue
                raise


    def fetch_all(self, address: str) -> Dict:
        """Synchronous geocode → 5-way fan-out → risk. Thin wrapper over _run_sources.

        For the non-blocking, per-subagent path with live progress, see
        utils.orchestration.start_pipeline (which wraps these same _fetch_* methods).
        """
        geo = self._geocode(address)
        return {
            "geo": geo,
            **self._run_sources(geo),
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }

    def _run_sources(self, geo: Dict) -> Dict:
        """Fan out the 5 data-source fetches in parallel and assemble the result body.

        Returns the body dict (weather/crime/infrastructure/earthquakes/risk_score)
        without `geo` or `fetched_at` — the caller adds those. NWS alerts are merged
        into `weather["alerts"]`, matching the orchestration path.
        """
        lat, lon = geo["lat"], geo["lon"]
        city_key = self._detect_city(geo.get("city", ""), geo.get("state", ""))

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            fut_weather = executor.submit(self._fetch_weather, lat, lon)
            fut_nws = executor.submit(self._fetch_nws_alerts, lat, lon)
            fut_crime = executor.submit(self._fetch_crime, lat, lon, city_key, geo.get("state", ""), geo)
            fut_infra = executor.submit(self._fetch_311, lat, lon, city_key)
            fut_quakes = executor.submit(self._fetch_earthquakes, lat, lon)

            weather = fut_weather.result()
            nws_alerts = fut_nws.result()
            crime = fut_crime.result()
            infra = fut_infra.result()
            quakes = fut_quakes.result()

        weather["alerts"] = nws_alerts

        risk = self._compute_risk(crime, weather, infra, quakes, city_key)

        return {
            "weather": weather,
            "crime": crime,
            "infrastructure": infra,
            "earthquakes": quakes,
            "risk_score": risk,
        }


    def _geocode(self, address: str) -> Dict:
        """Nominatim (OSM) — free, no key required."""
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": address, "format": "json", "addressdetails": 1, "limit": 1, "countrycodes": "us"}
        r = self._safe_get(url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        results = r.json()
        if not results:
            raise ValueError(f"Could not geocode: {address}")
        top = results[0]
        addr = top.get("address", {})
        return {
            "lat": float(top["lat"]),
            "lon": float(top["lon"]),
            "display_name": top.get("display_name", address),
            "city": addr.get("city") or addr.get("town") or addr.get("village") or "",
            "state": addr.get("state", ""),
            "zip": addr.get("postcode", ""),
            "county": addr.get("county", ""),
        }


    def _fetch_weather(self, lat: float, lon: float) -> Dict:
        if not OPENWEATHER_KEY:
            return self._weather_stub(lat, lon)

        cur_url = "https://api.openweathermap.org/data/2.5/weather"
        fc_url = "https://api.openweathermap.org/data/2.5/forecast"

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                fut_cur = executor.submit(self._safe_get, cur_url, params={"lat": lat, "lon": lon, "appid": OPENWEATHER_KEY, "units": "imperial"}, timeout=10)
                fut_fc = executor.submit(self._safe_get, fc_url, params={"lat": lat, "lon": lon, "appid": OPENWEATHER_KEY, "units": "imperial", "cnt": 8}, timeout=10)

                cur = fut_cur.result()
                fc = fut_fc.result()

            cur.raise_for_status()
            cd = cur.json()

            fc.raise_for_status()
            fd = fc.json()
        except Exception as e:
            logger.warning("[Weather] Fetch failed, falling back to stub: %s", e)
            return self._weather_stub(lat, lon)

        try:
            current = {
                "temp_f": round(cd["main"]["temp"]),
                "feels_like_f": round(cd["main"]["feels_like"]),
                "humidity": cd["main"]["humidity"],
                "pressure": cd["main"]["pressure"],
                "wind_mph": round(cd["wind"].get("speed", 0)),
                "wind_dir": cd["wind"].get("deg", 0),
                "visibility_mi": round(cd.get("visibility", 10000) / 1609, 1),
                "description": cd["weather"][0]["description"].title(),
                "icon": cd["weather"][0]["icon"],
                "clouds": cd["clouds"]["all"],
                "uv_index": cd.get("uvi"),
                "sunrise": datetime.fromtimestamp(cd["sys"]["sunrise"]).strftime("%I:%M %p"),
                "sunset": datetime.fromtimestamp(cd["sys"]["sunset"]).strftime("%I:%M %p"),
            }
        except (KeyError, TypeError, IndexError) as e:
            logger.warning("[Weather] Malformed response, falling back to stub: %s", e)
            return self._weather_stub(lat, lon)

        forecast = []
        for item in fd.get("list", []):
            try:
                forecast.append({
                    "dt": item["dt_txt"],
                    "temp_f": round(item["main"]["temp"]),
                    "description": item["weather"][0]["description"].title(),
                    "wind_mph": round(item["wind"].get("speed", 0)),
                    "humidity": item["main"]["humidity"],
                    "pop": round(item.get("pop", 0) * 100),
                })
            except (KeyError, TypeError, IndexError):
                continue

        return {"current": current, "forecast": forecast, "alerts": []}

    def _weather_stub(self, lat, lon):
        """Fallback stub if no OpenWeather key."""
        return {
            "current": {
                "temp_f": 72, "feels_like_f": 70, "humidity": 55,
                "pressure": 1013, "wind_mph": 8, "wind_dir": 180,
                "visibility_mi": 10.0, "description": "Partly Cloudy",
                "icon": "02d", "clouds": 30, "uv_index": None,
                "sunrise": "6:30 AM", "sunset": "7:45 PM",
            },
            "forecast": [],
            "alerts": [],
            "stub": True,
        }

    def _fetch_nws_alerts(self, lat: float, lon: float) -> List[Dict]:
        """National Weather Service active alerts — no key needed."""
        try:
            url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
            r = self._safe_get(url, headers={**HEADERS, "Accept": "application/geo+json"}, timeout=10)
            r.raise_for_status()
            features = r.json().get("features", [])
            alerts = []
            for f in features[:5]:
                p = f.get("properties", {})
                alerts.append({
                    "event": p.get("event", ""),
                    "severity": p.get("severity", ""),
                    "headline": p.get("headline", ""),
                    "description": (p.get("description", "") or "")[:300],
                    "onset": p.get("onset", ""),
                    "expires": p.get("expires", ""),
                })
            return alerts
        except Exception as e:
            logger.warning("[NWS] alerts fetch failed: %s", e)
            return []


    def _fetch_crime(self, lat: float, lon: float, city_key: str, state: str = "", geo: Dict = None) -> Dict:
        incidents = []

        if city_key and city_key in SOCRATA_ENDPOINTS:
            incidents = self._fetch_socrata_crime(lat, lon, city_key)

        fbi_stats = self._fetch_fbi_stats(state)

        fbi_summary = {}
        if not incidents:
            geo = geo or {}
            fbi_summary = self._fetch_fbi_agency(
                lat, lon, state, geo.get("city", ""), geo.get("county", "")
            )

        type_counts = {}
        for inc in incidents:
            t = inc.get("type", "Other")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "incidents": incidents[:200],
            "total_count": len(incidents),
            "type_counts": type_counts,
            "fbi_stats": fbi_stats,
            "fbi_summary": fbi_summary,
            "period_days": 30,
        }

    def _fetch_socrata_crime(self, lat: float, lon: float, city_key: str) -> List[Dict]:
        url = SOCRATA_ENDPOINTS[city_key]
        since = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00.000")
        headers = {"X-App-Token": SOCRATA_TOKEN} if SOCRATA_TOKEN else {}

        if city_key == "chicago":
            params = {
                "$limit": 500,
                "$where": f"date >= '{since}'",
                "$select": "date,primary_type,description,location_description,latitude,longitude,block",
                "$order": "date DESC",
            }
        elif city_key == "new york":
            params = {
                "$limit": 500,
                "$where": f"cmplnt_fr_dt >= '{since}'",
                "$select": "cmplnt_fr_dt,ofns_desc,law_cat_cd,boro_nm,latitude,longitude",
                "$order": "cmplnt_fr_dt DESC",
            }
        else:
            params = {"$limit": 300, "$order": ":id DESC"}

        try:
            r = self._safe_get(url, params=params, headers=headers, timeout=12)
            r.raise_for_status()
            raw = r.json()
        except Exception as e:
            logger.warning("[Socrata:%s] crime fetch failed: %s", city_key, e)
            return []

        incidents = []
        for row in raw:
            try:
                rlat = float(row.get("latitude") or row.get("lat") or 0)
                rlon = float(row.get("longitude") or row.get("lon") or row.get("lng") or 0)
            except (ValueError, TypeError):
                rlat, rlon = lat, lon

            raw_type = (
                row.get("primary_type") or
                row.get("ofns_desc") or
                row.get("crime_type") or
                row.get("incident_type_primary") or
                row.get("offense_type") or
                row.get("highest_nibrs_ucr_offense_description") or
                row.get("crime_category") or
                row.get("incident_category") or
                row.get("incident_description") or
                "Unknown"
            )
            if not isinstance(raw_type, str) or not raw_type.strip():
                raw_type = "Unknown"
            
            raw_type_upper = raw_type.upper()
            if any(x in raw_type_upper for x in ["THEFT", "BURGLARY", "LARCENY", "ROBBERY"]):
                norm_type = "Theft & Burglary"
            elif any(x in raw_type_upper for x in ["ASSAULT", "BATTERY", "HOMICIDE", "MURDER"]):
                norm_type = "Violent Crime"
            elif any(x in raw_type_upper for x in ["VEHICLE", "AUTO", "MOTOR"]):
                norm_type = "Vehicle Incident"
            elif any(x in raw_type_upper for x in ["DRUG", "NARCOTIC"]):
                norm_type = "Drug Offense"
            elif any(x in raw_type_upper for x in ["FRAUD", "DECEPTIVE", "FORGERY"]):
                norm_type = "Fraud & Deception"
            elif "TRESPASS" in raw_type_upper:
                norm_type = "Trespassing"
            elif any(x in raw_type_upper for x in ["WEAPON", "FIREARM"]):
                norm_type = "Weapons Offense"
            elif any(x in raw_type_upper for x in ["DAMAGE", "MISCHIEF", "VANDALISM"]):
                norm_type = "Property Damage/Vandalism"
            elif "UNKNOWN" not in raw_type_upper:
                norm_type = raw_type.title()
            else:
                norm_type = "Other/Unknown"

            incidents.append({
                "type": norm_type,
                "description": row.get("description") or row.get("law_cat_cd") or "",
                "date": row.get("date") or row.get("cmplnt_fr_dt") or "",
                "location": row.get("location_description") or row.get("boro_nm") or "",
                "block": row.get("block") or "",
                "lat": rlat or lat,
                "lon": rlon or lon,
            })
        return incidents

    def _fetch_fbi_stats(self, state_name: str) -> Dict:
        """FBI Crime Data Explorer — returns state-level violent crime stats."""
        if not FBI_API_KEY:
            return {"note": "Set FBI_CRIME_API_KEY for national crime statistics."}
        state_abbr = STATE_ABBREVS.get(state_name, "")
        if not state_abbr:
            return {"note": f"No FBI state mapping for: {state_name!r}"}
        try:
            url = f"https://api.usa.gov/crime/fbi/cde/summarized/state/{state_abbr}/violent-crime"
            r = self._safe_get(url, params={"API_KEY": FBI_API_KEY}, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("[FBI] stats fetch failed for state=%s: %s", state_abbr, e)
            return {"note": "FBI API unavailable."}

    def _fetch_fbi_agency(self, lat: float, lon: float, state_name: str,
                          city: str = "", county: str = "") -> Dict:
        if not FBI_API_KEY:
            return {}
        state_abbr = STATE_ABBREVS.get(state_name, "")
        if not state_abbr:
            return {}

        agency = self._find_agency(lat, lon, state_abbr, city, county)
        ori = agency.get("ori") if agency else ""
        if not ori:
            return {}

        summary = {
            "agency_name": agency.get("agency_name") or agency.get("name") or "Local agency",
            "ori": ori,
            "county": agency.get("county_name") or county or "",
            "state_abbr": state_abbr,
            "source": "FBI Crime Data Explorer",
        }

        violent = self._fbi_agency_offense(ori, "violent-crime")
        if violent:
            summary["violent_year"], summary["violent_crime"] = violent

        prop = self._fbi_agency_offense(ori, "property-crime")
        if prop:
            summary["property_year"], summary["property_crime"] = prop

        if "violent_crime" not in summary and "property_crime" not in summary:
            return {}
        return summary

    def _find_agency(self, lat: float, lon: float, state_abbr: str,
                     city: str = "", county: str = "") -> Dict:
        try:
            url = f"{FBI_CDE_BASE}/agency/byStateAbbr/{state_abbr}"
            r = self._safe_get(url, params={"API_KEY": FBI_API_KEY}, timeout=12)
            r.raise_for_status()
            agencies = self._normalize_agency_list(r.json())
        except Exception as e:
            logger.warning("[FBI] agency lookup failed for state=%s: %s", state_abbr, e)
            return {}

        located = []
        for a in agencies:
            try:
                alat = float(a.get("latitude"))
                alon = float(a.get("longitude"))
            except (TypeError, ValueError):
                continue
            located.append((self._haversine_km(lat, lon, alat, alon), a))
        if located:
            located.sort(key=lambda x: x[0])
            return located[0][1]

        city_l = (city or "").lower().strip()
        if city_l:
            for a in agencies:
                name = (a.get("agency_name") or a.get("name") or "").lower()
                if city_l in name:
                    return a

        county_l = (county or "").lower().replace(" county", "").strip()
        if county_l:
            for a in agencies:
                cn = (a.get("county_name") or "").lower()
                if county_l and county_l in cn:
                    return a

        return {}

    @staticmethod
    def _normalize_agency_list(data) -> List[Dict]:
        if isinstance(data, list):
            return [a for a in data if isinstance(a, dict)]
        if isinstance(data, dict):
            if isinstance(data.get("agencies"), list):
                return [a for a in data["agencies"] if isinstance(a, dict)]
            out = []
            for key, val in data.items():
                if isinstance(val, dict):
                    out.append(val if "ori" in val else {**val, "ori": key})
                elif isinstance(val, list):
                    out.extend(a for a in val if isinstance(a, dict))
            return out
        return []

    def _fbi_agency_offense(self, ori: str, offense: str):
        try:
            url = f"{FBI_CDE_BASE}/summarized/agency/{ori}/{offense}"
            r = self._safe_get(url, params={"API_KEY": FBI_API_KEY}, timeout=12)
            r.raise_for_status()
            return self._cde_latest_total(r.json())
        except Exception as e:
            logger.warning("[FBI] agency offense fetch failed ori=%s offense=%s: %s", ori, offense, e)
            return None

    @staticmethod
    def _cde_latest_total(payload):
        candidates = []

        def collect(series):
            best = None
            for yk, yv in series.items():
                year = str(yk)[:4]
                if not year.isdigit() or yv is None:
                    continue
                try:
                    value = int(float(yv))
                except (TypeError, ValueError):
                    continue
                if best is None or year > best[0]:
                    best = (year, value)
            if best:
                candidates.append((int(best[0]), best[1]))

        if isinstance(payload, dict):
            offenses = payload.get("offenses")
            actuals = offenses.get("actuals") if isinstance(offenses, dict) else None
            if isinstance(actuals, dict):
                for key, series in actuals.items():
                    if "united states" in str(key).lower() or "national" in str(key).lower():
                        continue
                    if isinstance(series, dict):
                        collect(series)
            if not candidates:
                yearish = {k: v for k, v in payload.items() if str(k)[:4].isdigit()}
                if yearish:
                    collect(yearish)
        elif isinstance(payload, list):
            series = {}
            for row in payload:
                if not isinstance(row, dict):
                    continue
                year = row.get("data_year") or row.get("year")
                value = row.get("actual")
                if value is None:
                    value = row.get("value")
                if value is None:
                    value = row.get("count")
                if year is not None and value is not None:
                    series[year] = value
            if series:
                collect(series)

        if not candidates:
            return None
        candidates.sort()
        return candidates[-1]

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        rad = math.pi / 180.0
        a = (math.sin((lat2 - lat1) * rad / 2) ** 2 +
             math.cos(lat1 * rad) * math.cos(lat2 * rad) *
             math.sin((lon2 - lon1) * rad / 2) ** 2)
        return 2 * 6371.0 * math.asin(min(1.0, math.sqrt(a)))


    def _fetch_311(self, lat: float, lon: float, city_key: str) -> Dict:
        complaints = []
        if city_key and city_key in CITY_311_ENDPOINTS:
            complaints = self._fetch_311_city(lat, lon, city_key)

        categories = {}
        for c in complaints:
            cat = c.get("category", "Other")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "complaints": complaints[:100],
            "total": len(complaints),
            "categories": categories,
        }

    def _fetch_311_city(self, lat: float, lon: float, city_key: str) -> List[Dict]:
        url = CITY_311_ENDPOINTS[city_key]
        since = (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%dT00:00:00.000")
        headers = {"X-App-Token": SOCRATA_TOKEN} if SOCRATA_TOKEN else {}

        if city_key == "chicago":
            params = {"$limit": 200, "$where": f"creation_date >= '{since}'", "$order": "creation_date DESC"}
        elif city_key == "new york":
            params = {"$limit": 200, "$where": f"created_date >= '{since}'", "$order": "created_date DESC"}
        else:
            params = {"$limit": 150, "$order": ":id DESC"}

        try:
            r = self._safe_get(url, params=params, headers=headers, timeout=12)
            r.raise_for_status()
            raw = r.json()
        except Exception as e:
            logger.warning("[311:%s] fetch failed: %s", city_key, e)
            return []

        complaints = []
        for row in raw:
            complaints.append({
                "category": row.get("type_of_service_request") or row.get("complaint_type") or row.get("service_name") or "Other",
                "status": row.get("status") or row.get("resolution_action") or "Open",
                "date": row.get("creation_date") or row.get("created_date") or row.get("requested_datetime") or "",
                "address": row.get("street_address") or row.get("incident_address") or row.get("address") or "",
            })
        return complaints


    def _fetch_earthquakes(self, lat: float, lon: float) -> List[Dict]:
        try:
            url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
            params = {
                "format": "geojson",
                "latitude": lat,
                "longitude": lon,
                "maxradiuskm": 500,
                "minmagnitude": 2.0,
                "orderby": "time",
                "limit": 10,
            }
            r = self._safe_get(url, params=params, timeout=10)
            r.raise_for_status()
            features = r.json().get("features", [])
            quakes = []
            for f in features:
                p = f.get("properties")
                if not p:
                    continue
                try:
                    quakes.append({
                        "magnitude": p.get("mag"),
                        "place": p.get("place", ""),
                        "time": datetime.fromtimestamp(p["time"] / 1000).strftime("%Y-%m-%d %H:%M UTC"),
                        "url": p.get("url", ""),
                    })
                except (KeyError, TypeError, ValueError):
                    continue
            return quakes
        except Exception as e:
            logger.warning("[USGS] earthquake fetch failed: %s", e)
            return []


    def _compute_risk(self, crime: Dict, weather: Dict, infra: Dict, quakes: List, city_key: str = "") -> Dict:
        population = CITY_POPULATIONS.get(city_key, DEFAULT_POPULATION)
        pop_100k = population / 100_000

        crime_count = crime.get("total_count", 0)
        crime_score = min(100, int((crime_count / pop_100k) * 3.3))
        crime_label = self._score_label(crime_score)

        nws = weather.get("alerts", [])
        w_sev = {"Extreme": 100, "Severe": 75, "Moderate": 40, "Minor": 20}
        weather_score = max((w_sev.get(a.get("severity", ""), 0) for a in nws), default=0)
        if not nws:
            cur = weather.get("current", {})
            wind = cur.get("wind_mph", 0)
            if wind > 50:
                weather_score = 60
            elif wind > 30:
                weather_score = 30
        weather_label = self._score_label(weather_score)

        infra_count = infra.get("total", 0)
        infra_score = min(100, int((infra_count / pop_100k) * 5))
        infra_label = self._score_label(infra_score)

        quake_score = 0
        for q in quakes:
            mag = q.get("magnitude") or 0
            if mag >= 5:
                quake_score = max(quake_score, 70)
            elif mag >= 3:
                quake_score = max(quake_score, 30)

        overall = min(100, int(
            crime_score * 0.45 +
            weather_score * 0.30 +
            infra_score * 0.15 +
            quake_score * 0.10
        ))
        overall_label = self._score_label(overall)

        return {
            "overall": overall,
            "overall_label": overall_label,
            "crime_score": crime_score,
            "crime_label": crime_label,
            "weather_score": weather_score,
            "weather_label": weather_label,
            "infra_score": infra_score,
            "infra_label": infra_label,
            "quake_score": quake_score,
        }

    @staticmethod
    def _score_label(score: int) -> str:
        if score >= 75:
            return "Critical"
        if score >= 50:
            return "High"
        if score >= 25:
            return "Moderate"
        return "Low"

    @staticmethod
    def _detect_city(city: str, state: str) -> str:
        city_lower = city.lower().strip()
        all_keys = set(SOCRATA_ENDPOINTS) | set(CITY_311_ENDPOINTS)
        if city_lower in all_keys:
            return city_lower
        for key in all_keys:
            if city_lower.startswith(key):
                return key
        return ""