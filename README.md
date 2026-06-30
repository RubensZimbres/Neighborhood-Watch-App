# NeighborhoodAlert

**Real-Time Neighborhood Safety Intelligence Platform**

NeighborhoodAlert aggregates crime reports, weather alerts, 311 infrastructure
complaints, and seismic data for any US address, normalizes them into a single
composite risk score, and runs the aggregated picture through Google Gemini to
produce an actionable safety briefing.

The data pipeline is built as a **multi-agent orchestration layer**: each data
source is an isolated Google ADK agent in a dependency graph, the graph runs on a
background thread, and the Streamlit UI streams live per-agent progress while
the work executes.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Multi-Agent Orchestration Layer](#multi-agent-orchestration-layer)
3. [Risk Scoring](#risk-scoring)
4. [Data Sources](#data-sources)
5. [Security Features](#security-features)
6. [Project Structure](#project-structure)
7. [Prerequisites](#prerequisites)
8. [API Keys](#api-keys-where-to-get-them)
9. [Running Locally](#running-locally)
10. [Running the Tests](#running-the-tests)
11. [Deploying to Google Cloud Run](#deploying-to-google-cloud-run)
12. [Deploying to Streamlit Cloud](#deploying-to-streamlit-cloud)
13. [Licenses](#licenses)

---

## Architecture

```
                          Streamlit UI (app.py)
                                  |
              start_pipeline(address, fetcher, analyzer)
                                  |
                       background daemon thread
                                  |
                    ADK Runner (SequentialAgent)
                                  |
        +----------+----------+----------+----------+-----------+
        |          |          |          |          |           |
     weather      nws       crime       infra    earthquakes    |   (fan out off geocode)
        |          |          |          |          |           |
        +----------+----+-----+----------+----------+           |
                        |                                       |
                      risk  <--------------------------------- geocode (root)
                        |
                    ai_briefing  (Google Gemini)
                                  |
                          ProgressBoard
                                  |
            main thread polls snapshot() and re-renders
```

The application has two execution paths over the same underlying fetch methods:

- **Synchronous path** (`DataFetcher.fetch_all`): geocode, then a 5-way parallel
  fan-out, then risk scoring. Used by tests and any non-UI caller.
- **Orchestrated path** (`utils/orchestration.start_pipeline`): the same fetches
  wrapped as Google ADK agents in a dependency graph, executed on a background
  thread with live progress and the AI briefing as the final node. Used by the UI.

---

## Multi-Agent Orchestration Layer

`utils/orchestration.py` turns the flat fetch-and-analyze flow into an explicit
directed acyclic graph (DAG) of named, isolated Google ADK agents.

### Core abstractions

| Component | Responsibility |
|---|---|
| `NodeAgent` | A custom ADK `BaseAgent`: a callable `body(deps)`, its declared `node_deps`, and an `on_error` policy (a stub value, a stub factory, or `PROPAGATE` to abort). It reads its dependencies from session state, runs the blocking fetch in a worker thread, and writes its result back as a state delta. |
| `ParallelAgent` / `SequentialAgent` | ADK workflow agents that compose the nodes: the five data sources run under a `ParallelAgent`, wrapped by a top-level `SequentialAgent` of geocode → sources → risk → ai_briefing. |
| `ProgressBoard` | A thread-safe status board. The worker thread writes only here; the UI reads deep-copied plain-dict snapshots. |
| `build_pipeline` | Constructs the 8 nodes as thin closures over existing `DataFetcher` / `AIAnalyzer` methods and assembles the ADK agent tree, plus the final assembler. |
| `start_pipeline` | Non-blocking entry point: drives the ADK `Runner` on a daemon thread and returns the `ProgressBoard` immediately. |

### The pipeline graph

```
geocode (root, no stub - a geocode failure aborts the run)
  |-- weather       (stub: synthetic current conditions)
  |-- nws           (stub: empty alert list)
  |-- crime         (stub: empty incident set)
  |-- infra         (stub: empty complaint set)
  |-- earthquakes   (stub: empty quake list)
risk          (depends on all 5 sources; merges NWS into weather, scores)
ai_briefing   (depends on risk; calls Gemini; stub: "AI analysis unavailable.")
```

### Design properties

- **Per-source error isolation.** If a data source raises, its agent is marked
  `failed`, its `on_error` stub is substituted, and siblings and downstream nodes
  continue. One flaky API never crashes the dashboard.
- **Root failure propagation.** The `geocode` root has no stub. If geocoding fails
  (for example, an unresolvable address), the run aborts and the error surfaces as
  a single clean message in the UI.
- **Non-blocking UI.** The orchestration runs on a daemon thread. The Streamlit
  main thread polls `ProgressBoard.snapshot()` on a short interval and re-renders a
  live trace (queued / running / done / failed plus elapsed milliseconds) until the
  board reports done. The worker thread never touches Streamlit state.
- **Result caching.** Completed results are cached in session state by address for
  five minutes, so repeated lookups skip the pipeline entirely.

---

## Risk Scoring

Each query produces a composite risk score from 0 to 100, built from four weighted
components:

| Component | Weight | Method |
|---|---|---|
| Crime | 45% | Severity-weighted incident rate with an absolute serious-crime floor (30-day window), or FBI annual totals when no incident feed exists |
| Weather | 30% | NWS alert severity, or wind-speed fallback when no alerts are active |
| Infrastructure | 15% | Per-capita 311 complaint rate (complaints per 100k residents, 14-day window) |
| Seismic | 10% | USGS earthquake magnitude within a 500 km radius |

The infrastructure score is normalized by city population so the same raw
complaint count produces a proportionally higher score in a small city than in a
large one. Supported city populations are baked in; unknown cities default to
500,000.

### Crime Index

The Crime Index is **severity-weighted**, not a flat incident count, so serious
offenses drive the score far more than low-harm reports. It is the larger of two
signals:

- **Severity-weighted volume** — incidents are weighted by type before per-capita
  normalization (Violent Crime ×10, Weapons ×8, Theft & Burglary ×4, Vehicle ×3,
  Drug/Fraud/Vandalism ×2, everything else ×1), keeping cities of different sizes
  comparable.
- **Serious-crime floor** — an absolute component (`violent × 1.8 +
  theft/burglary × 0.5`) ensures that a meaningful raw count of violent or
  property crime always registers as at least *Moderate*, regardless of city
  population. For example, ~24 violent incidents in the 30-day window scores
  *Moderate* on its own and tips into *High* once theft/burglary is added.

When a city has no incident-level feed, the index falls back to **FBI Crime Data
Explorer** annual violent- and property-crime totals, scored per capita (these
previously always scored 0). The severity weights and floor constants live at the
top of `utils/data_fetcher.py` (`SEVERITY_WEIGHTS`, `VIOLENT_FLOOR_PTS`,
`PROPERTY_FLOOR_PTS`) and are easy to retune.

### Coverage

The application is **US only**: geocoding is restricted to the United States
(`countrycodes=us`), and because geocoding is the root of the pipeline, non-US
addresses do not resolve. Coverage within the US varies by layer:

| Layer | Sources | Coverage |
|---|---|---|
| Geocoding | Nominatim (OpenStreetMap), free, no key | US addresses only (gates the whole pipeline) |
| Crime (incident-level) | Socrata Open Data | 10 cities: Chicago, NYC, LA, SF, Seattle, Dallas, Austin, Denver, Houston, Boston |
| Crime (agency aggregates) | FBI Crime Data Explorer | Any US city (nearest reporting agency) |
| Crime (statistics) | FBI Crime Data Explorer | Any US state |
| Infrastructure | 311 Open Data (Socrata) | 6 cities: Chicago, NYC, SF, LA, Seattle, Boston; empty elsewhere |
| Weather | OpenWeatherMap + NWS Alerts | Any resolved US point |
| Seismic | USGS Earthquake Feed, free, no key | Any resolved US point |
| AI Analysis | Google Gemini 2.0 Flash via Vertex AI | Requires GCP account |

When an address resolves to one of the listed cities, the crime panel shows the
incident-level map. For **any other US city**, the crime panel falls back to
**FBI Crime Data Explorer agency aggregates**: the application looks up the law
enforcement agency nearest to the geocoded point and shows its most recent annual
violent-crime and property-crime totals, so the panel is no longer empty. These
annual totals also feed the Crime Index (scored per capita) so the risk score
reflects crime even outside the incident-level cities. The 311 panel remains
city-limited (empty outside the six listed cities), and the incident-map markers
still require incident-level data and are therefore only populated for the listed
crime cities.

---

## Data Sources

NeighborhoodAlert pulls exclusively from public and open-data APIs. Every source
degrades to a safe stub on failure, so the application runs even when a source is
unreachable or no key is configured. The endpoints below are the exact URLs called
by `utils/data_fetcher.py`.

### Summary

| Domain | Provider | Endpoint | Auth |
|---|---|---|---|
| Geocoding | Nominatim (OpenStreetMap) | `https://nominatim.openstreetmap.org/search` | None |
| Current weather | OpenWeatherMap | `https://api.openweathermap.org/data/2.5/weather` | API key |
| Forecast | OpenWeatherMap | `https://api.openweathermap.org/data/2.5/forecast` | API key |
| Weather alerts | National Weather Service | `https://api.weather.gov/alerts/active` | None |
| State crime stats | FBI Crime Data Explorer | `https://api.usa.gov/crime/fbi/cde/summarized/state/{STATE}/violent-crime` | API key |
| Agency crime aggregates | FBI Crime Data Explorer | `https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{STATE}` and `.../summarized/agency/{ORI}/{offense}` | API key |
| City crime incidents | Socrata Open Data (per city) | see table below | App token (optional) |
| 311 infrastructure | Socrata Open Data (per city) | see table below | App token (optional) |
| Seismic | USGS Earthquake Catalog | `https://earthquake.usgs.gov/fdsnws/event/1/query` | None |

### Geocoding: Nominatim (OpenStreetMap)

- Endpoint: `https://nominatim.openstreetmap.org/search`
- Auth: none. A descriptive `User-Agent` header is sent per the Nominatim usage policy.
- Scope: US addresses only (`countrycodes=us`); non-US addresses do not resolve.
- Returns latitude, longitude, city, state, ZIP, and county for the queried address.
- This is the root of the pipeline; if it fails, the run aborts with a clear message.

### Weather: OpenWeatherMap

- Current conditions: `https://api.openweathermap.org/data/2.5/weather`
- 5-day / 3-hour forecast: `https://api.openweathermap.org/data/2.5/forecast`
- Auth: `OPENWEATHER_API_KEY`. Without a key, the app returns synthetic stub weather.
- Units: imperial.

### Weather alerts: National Weather Service (NWS)

- Endpoint: `https://api.weather.gov/alerts/active?point={lat},{lon}`
- Auth: none (public domain, US government).
- Active alerts are merged into the weather payload and feed the weather risk score.

### Crime statistics and aggregates: FBI Crime Data Explorer

Two FBI layers, both authenticated with `FBI_CRIME_API_KEY`:

State summary (any US state):

- Endpoint: `https://api.usa.gov/crime/fbi/cde/summarized/state/{STATE}/violent-crime`
- The two-letter state code is derived from the geocoded state name, for example
  `https://api.usa.gov/crime/fbi/cde/summarized/state/IL/violent-crime`.

Agency aggregates (any US city, used when no incident-level feed exists):

- Agency directory: `https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{STATE}`
- Agency totals: `https://api.usa.gov/crime/fbi/cde/summarized/agency/{ORI}/{offense}`
  where `offense` is `violent-crime` or `property-crime`.
- The application lists agencies in the geocoded state, selects the one nearest to
  the address by latitude/longitude (falling back to a city-name or county-name
  match), then reports that agency's most recent annual violent-crime and
  property-crime totals. All responses are parsed defensively and degrade to an
  empty panel if the data is unavailable.

### City crime incidents: Socrata Open Data

Per-city incident-level datasets. Auth is the optional `SOCRATA_APP_TOKEN` (sent as
the `X-App-Token` header), which raises rate limits; anonymous access also works.

| City | Crime dataset endpoint |
|---|---|
| Chicago | `https://data.cityofchicago.org/resource/ijzp-q8t2.json` |
| New York | `https://data.cityofnewyork.us/resource/5uac-w243.json` |
| Los Angeles | `https://data.lacity.org/resource/2nrs-mtv8.json` |
| San Francisco | `https://data.sfgov.org/resource/wg3w-h783.json` |
| Seattle | `https://data.seattle.gov/resource/tazs-3rd5.json` |
| Dallas | `https://www.dallasopendata.com/resource/qv6i-rri7.json` |
| Austin | `https://data.austintexas.gov/resource/fdj4-gpfu.json` |
| Denver | `https://data.denvergov.org/resource/mnz9-vjy7.json` |
| Houston | `https://data.houstontx.gov/resource/kubn-qncu.json` |
| Boston | `https://data.boston.gov/resource/crime.json` |

### 311 infrastructure complaints: Socrata Open Data

Per-city 311 service-request datasets. Same optional `SOCRATA_APP_TOKEN` auth.

| City | 311 dataset endpoint |
|---|---|
| Chicago | `https://data.cityofchicago.org/resource/v6vf-nfxy.json` |
| New York | `https://data.cityofnewyork.us/resource/erm2-nwe9.json` |
| San Francisco | `https://data.sfgov.org/resource/vw6y-z8j6.json` |
| Los Angeles | `https://data.lacity.org/resource/rq3b-xjk8.json` |
| Seattle | `https://data.seattle.gov/resource/55dj-4iis.json` |
| Boston | `https://data.boston.gov/resource/wc8w-nujj.json` |

### Seismic: USGS Earthquake Catalog

- Endpoint: `https://earthquake.usgs.gov/fdsnws/event/1/query`
- Auth: none (public domain, US government).
- Query: GeoJSON events within a 500 km radius of the geocoded point, minimum
  magnitude 2.0, most recent first, limited to 10 results.

### AI analysis: Google Gemini (Vertex AI)

- Model: `gemini-2.0-flash-001` via Vertex AI.
- Auth: Application Default Credentials plus `GCP_PROJECT_NAME` and `GCP_LOCATION`.
- Input: the aggregated risk picture produced by all of the sources above.
- Without GCP configured, the app returns a deterministic fallback briefing.

---

## Security Features

| Feature | Detail |
|---|---|
| HTML Injection Prevention | All dynamic data interpolated into `unsafe_allow_html=True` blocks is escaped through a centralized `_esc()` helper, including crime types, NWS headlines, weather descriptions, 311 categories, and user-provided addresses. |
| No Committed Credentials | API keys are loaded exclusively from environment variables via `.env`. The `.env.example` template contains only placeholders. |
| Graceful API Degradation | Every external call returns safe stub data on failure; the app never crashes from a third-party outage. |
| Retry on Transient Failures | A `_safe_get()` HTTP helper retries once on 5xx and connection errors with a one-second backoff. |
| Defensive Response Parsing | Weather and earthquake parsers catch malformed responses and fall back to stubs. |
| Input Boundary Checks | Crime incidents capped at 200, 311 complaints at 100, NWS alerts at 5, earthquakes at 10, forecast items at 8. |
| AI Content Isolation | The AI-generated briefing body is rendered with `unsafe_allow_html=False`; only the surrounding layout uses raw HTML. |
| Thread Isolation | The orchestration worker thread writes only to a lock-guarded `ProgressBoard`; it never touches Streamlit session state. |

---

## Project Structure

```
.
├── app.py                       Streamlit entry point and non-blocking poll loop
├── utils/
│   ├── data_fetcher.py          DataFetcher: geocoding + all external data sources
│   ├── ai_analyzer.py           AIAnalyzer: Gemini prompt building and call
│   └── orchestration.py         NodeAgent / ADK agent tree / ProgressBoard / pipeline
├── components/
│   └── ui_components.py         Render functions, CSS, and the live agent trace
├── tests/
│   ├── conftest.py              Shared fixtures and HTTP mock helpers
│   ├── test_data_fetcher.py     Fetching, parsing, and risk-scoring tests
│   ├── test_ai_analyzer.py      Prompt building and Gemini call tests
│   ├── test_ui_components.py    Escaping, retry, and city-detection tests
│   └── test_orchestration.py    DAG ordering, isolation, status, thread tests
├── Dockerfile                   Cloud Run image (Streamlit headless on port 8080)
├── requirements.txt             Runtime dependencies
├── requirements-dev.txt         Test dependencies
└── .streamlit/config.toml       Theme configuration
```

---

## Prerequisites

- Python 3.10 or newer
- `pip` and `venv`
- For AI briefings: a Google Cloud project with the Vertex AI API enabled
- For Cloud Run deployment: the Google Cloud SDK (`gcloud`) installed and
  authenticated

The application runs without any API keys. Weather, crime, and AI analysis fall
back to demo or stub data. Add keys one at a time to enable live sources.

---

## API Keys (Where to Get Them)

### 1. OpenWeatherMap (weather data) - free

- URL: https://home.openweathermap.org/api_keys
- Steps: sign up, open the API keys tab, create a key
- Free tier: 60 calls per minute, 1M calls per month
- APIs needed: Current weather data, 5 Day / 3 Hour Forecast
- Environment variable: `OPENWEATHER_API_KEY`

### 2. FBI Crime Data Explorer - free

- URL: https://api.data.gov/signup/
- Steps: fill the form, the key is emailed instantly
- Free tier: unlimited (federal open data)
- Environment variable: `FBI_CRIME_API_KEY`

### 3. Socrata App Token (city crime and 311 data) - free

- URL: https://evergreen.data.socrata.com/signup
- Steps: sign up, open Profile, Developer Settings, create an app token
- Why: anonymous calls work but are rate-limited to roughly one request per second;
  a token raises limits across all city portals
- Environment variable: `SOCRATA_APP_TOKEN`

### 4. Google Cloud / Vertex AI (Gemini analysis) - pay as you go

- URL: https://console.cloud.google.com/vertex-ai
- Steps:
  1. Create a GCP project at https://console.cloud.google.com
  2. Enable billing
  3. Enable the Vertex AI API
  4. Authenticate locally: `gcloud auth application-default login`
  5. Set `GCP_PROJECT_NAME` to your project ID
- Cost: Gemini 2.0 Flash is approximately 0.075 USD per 1M input tokens
- Environment variables: `GCP_PROJECT_NAME`, `GCP_LOCATION`

---

## Running Locally

```bash
# 1. Get the project
cd neighborhoodalert

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate

# 3. Install runtime dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and add any keys you have (see the API Keys section)

# 5. (Optional) Authenticate with GCP for Vertex AI briefings
gcloud auth application-default login

# 6. Run the app
streamlit run app.py
```

The app opens at http://localhost:8501. Enter any US address and click Analyze.
The agent orchestration trace appears immediately and updates live as each
agent completes; the AI briefing renders as the final step.

### Environment variables

```
OPENWEATHER_API_KEY    OpenWeatherMap key (optional; stub weather without it)
FBI_CRIME_API_KEY      FBI Crime Data Explorer key (optional)
SOCRATA_APP_TOKEN      Socrata app token (optional; raises rate limits)
GCP_PROJECT_NAME       GCP project ID for Vertex AI (optional; fallback briefing without it)
GCP_LOCATION           Vertex AI region, for example us-central1
```

---

## Running the Tests

The test suite uses `pytest` with the standard-library `unittest.mock`. No live
network calls are made; all external APIs are mocked through shared fixtures in
`tests/conftest.py`.

```bash
# Install test dependencies (includes runtime deps)
pip install -r requirements-dev.txt

# Run the full suite
pytest -q

# Run a single module
pytest tests/test_orchestration.py -v

# Run with coverage (if pytest-cov is installed)
pytest --cov=utils --cov=components
```

### What is covered

| Module | Focus |
|---|---|
| `test_data_fetcher.py` | Geocoding, weather, NWS, FBI, Socrata crime, 311, earthquakes, severity-weighted crime-index math, and the synchronous `fetch_all` contract. |
| `test_ai_analyzer.py` | Client initialization, prompt construction, the Gemini call, and the fallback briefing. |
| `test_ui_components.py` | HTML escaping (XSS payloads), the `_safe_get` retry helper, and city detection. |
| `test_orchestration.py` | DAG topological ordering, per-source error isolation, root-failure propagation, status transitions, timing, and the background-thread smoke test. |

### Optional: end-to-end UI smoke test

Streamlit ships a headless test harness that runs `app.py` in a simulated runtime
with no server and no real network. This is a quick way to confirm the full poll
and rerun loop wires up correctly:

```python
from unittest.mock import patch
from utils.data_fetcher import DataFetcher
from utils.ai_analyzer import AIAnalyzer
from streamlit.testing.v1 import AppTest

GEO = {"lat": 41.88, "lon": -87.63, "display_name": "Chicago",
       "city": "Chicago", "state": "Illinois", "zip": "60601", "county": "Cook"}

with patch.object(DataFetcher, "_geocode", return_value=GEO), \
     patch.object(DataFetcher, "_fetch_weather", return_value={"current": {"temp_f": 72}, "forecast": [], "alerts": []}), \
     patch.object(DataFetcher, "_fetch_nws_alerts", return_value=[]), \
     patch.object(DataFetcher, "_fetch_crime", return_value={"incidents": [], "total_count": 0, "type_counts": {}, "fbi_stats": {}, "period_days": 30}), \
     patch.object(DataFetcher, "_fetch_311", return_value={"complaints": [], "total": 0, "categories": {}}), \
     patch.object(DataFetcher, "_fetch_earthquakes", return_value=[]), \
     patch.object(AIAnalyzer, "analyze", return_value="## Briefing OK"):
    at = AppTest.from_file("app.py", default_timeout=30).run()
    at.text_input[0].set_value("Chicago, IL")
    at.button[0].click().run()
    for _ in range(40):
        if at.session_state["last_data"]:
            break
        at.run()
    assert not at.exception
    assert at.session_state["last_data"]["analysis"] == "## Briefing OK"
```

---

## Deploying to Google Cloud Run

Cloud Run runs the container built from the included `Dockerfile`, which starts
Streamlit headless on port 8080.

### Step 1: Set the project and enable APIs

```bash
export PROJECT_ID="your-gcp-project-id"
gcloud config set project "$PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com
```

### Step 2: Build and deploy from source

Cloud Build reads the `Dockerfile` and pushes the image automatically.

```bash
gcloud run deploy neighborhoodalert \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "OPENWEATHER_API_KEY=your_key" \
  --set-env-vars "FBI_CRIME_API_KEY=your_key" \
  --set-env-vars "SOCRATA_APP_TOKEN=your_token" \
  --set-env-vars "GCP_PROJECT_NAME=$PROJECT_ID" \
  --set-env-vars "GCP_LOCATION=us-central1" \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 3
```

### Step 3: Grant Vertex AI access

The Cloud Run service account needs permission to call Vertex AI for briefings.

```bash
SA="$(gcloud iam service-accounts list \
  --filter='displayName:Compute Engine' \
  --format='value(email)')"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:$SA" \
  --role "roles/aiplatform.user"
```

### Step 4: Open the app

When the deploy completes, `gcloud` prints the service URL:

```
Service URL: https://neighborhoodalert-xxxxx-uc.a.run.app
```

### Using Secret Manager instead of plain env vars (recommended)

```bash
echo -n "your_key" | gcloud secrets create openweather-key --data-file=-
echo -n "your_key" | gcloud secrets create fbi-key --data-file=-

gcloud secrets add-iam-policy-binding openweather-key \
  --member "serviceAccount:$SA" --role "roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding fbi-key \
  --member "serviceAccount:$SA" --role "roles/secretmanager.secretAccessor"

gcloud run deploy neighborhoodalert \
  --source . \
  --region us-central1 \
  --set-secrets "OPENWEATHER_API_KEY=openweather-key:latest,FBI_CRIME_API_KEY=fbi-key:latest"
```

### Updating the deployment

```bash
gcloud run deploy neighborhoodalert --source . --region us-central1
```

### Local Docker test (optional)

```bash
docker build -t neighborhoodalert .
docker run --env-file .env -p 8080:8080 neighborhoodalert
# Open http://localhost:8080
```

---

## Deploying to Streamlit Cloud

1. Push the code to GitHub, excluding `.env`.
2. Go to https://share.streamlit.io and connect the repository, selecting `app.py`.
3. Add secrets under Settings, Secrets:

```toml
OPENWEATHER_API_KEY = "xxx"
FBI_CRIME_API_KEY   = "xxx"
SOCRATA_APP_TOKEN   = "xxx"
GCP_PROJECT_NAME    = "your-project"
GCP_LOCATION        = "us-central1"
```

4. For Vertex AI on Streamlit Cloud, add a GCP service-account JSON as a secret and
   authenticate with `google.oauth2.service_account.Credentials`.

---

## Licenses

- Crime and 311 data: Open Government License (Socrata cities)
- Weather: OpenWeatherMap Standard License and NWS (public domain)
- Geocoding: OpenStreetMap contributors (ODbL)
- Seismic: USGS (public domain)
- AI: Google Gemini via Vertex AI

---

## Disclaimer

This application is for informational purposes only. Risk scores are computed from
publicly available data and statistical models. They are not a substitute for
official emergency services or professional security advice. Always call 911 in an
emergency.
