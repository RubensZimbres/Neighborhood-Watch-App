"""
AIAnalyzer — wraps Google Gemini (Vertex AI) to produce a structured
neighborhood safety briefing from aggregated data.
"""

import os
import json
from datetime import datetime
from typing import Dict

try:
    from google import genai
    from google.genai import types as genai_types
    VERTEX_AVAILABLE = True
except ImportError:
    VERTEX_AVAILABLE = False

GCP_PROJECT  = os.environ.get("GCP_PROJECT_NAME", "")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
GEMINI_MODEL = "gemini-3.1-flash-preview"


class AIAnalyzer:
    def __init__(self):
        self._client = None
        if VERTEX_AVAILABLE and GCP_PROJECT:
            try:
                self._client = genai.Client(
                    vertexai=True,
                    project=GCP_PROJECT,
                    location=GCP_LOCATION,
                )
            except Exception as e:
                print(f"[AIAnalyzer] Vertex AI init failed: {e}")


    def analyze(self, data: Dict, address: str) -> str:
        prompt = self._build_prompt(data, address)
        if self._client:
            return self._call_gemini(prompt)
        return self._fallback_analysis(data, address)


    def _build_prompt(self, data: Dict, address: str) -> str:
        risk    = data.get("risk_score", {})
        crime   = data.get("crime", {})
        weather = data.get("weather", {})
        infra   = data.get("infrastructure", {})
        quakes  = data.get("earthquakes", [])
        cur     = weather.get("current", {})

        crime_types = json.dumps(crime.get("type_counts", {}), indent=2)
        nws_alerts  = json.dumps(weather.get("alerts", [])[:3], indent=2)
        infra_cats  = json.dumps(infra.get("categories", {}), indent=2)
        quake_txt   = json.dumps(quakes[:5], indent=2)

        return f"""
You are NeighborhoodAlert's AI Safety Analyst. Produce a concise, data-driven
neighborhood safety briefing for the address: **{address}**
Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}

## RAW DATA SUMMARY

### Risk Scores (0–100)
- Overall: {risk.get("overall", "N/A")} ({risk.get("overall_label", "")})
- Crime: {risk.get("crime_score", "N/A")} ({risk.get("crime_label", "")})
- Weather: {risk.get("weather_score", "N/A")} ({risk.get("weather_label", "")})
- Infrastructure: {risk.get("infra_score", "N/A")} ({risk.get("infra_label", "")})

### Crime (last 30 days)
Total incidents: {crime.get("total_count", 0)}
Breakdown by type:
{crime_types}

### Weather
Temp: {cur.get("temp_f", "?")}°F | Feels like: {cur.get("feels_like_f", "?")}°F
Wind: {cur.get("wind_mph", "?")} mph | Humidity: {cur.get("humidity", "?")}%
Conditions: {cur.get("description", "?")}
NWS Active Alerts:
{nws_alerts}

### Infrastructure (311 complaints, last 14 days)
Total: {infra.get("total", 0)}
Categories:
{infra_cats}

### Seismic (USGS, 500 km radius)
{quake_txt}

## YOUR TASK
Write a **Safety Briefing** in clean markdown using EXACTLY this structure.
Be specific, cite numbers, be concise. No fluff.

### Overall Assessment
One paragraph (3-4 sentences). State the risk level, the primary driver,
and one immediate recommendation.

### Crime Intelligence
- List the top 3 crime types by frequency with counts
- Note any concerning patterns (time, location, type escalation)
- Safety tip specific to the crime profile

### Weather & Environmental
- Current conditions impact on safety
- Any active NWS alerts or severe weather risks
- Seismic risk if applicable

### Infrastructure Status
- Top infrastructure complaint categories
- Any that pose direct safety risks (potholes, water main breaks, outages)
- Estimated resolution outlook

### Recommended Actions
Numbered list of 4-5 specific, actionable steps for a resident.

Keep the entire response under 500 words.
"""

    def _call_gemini(self, prompt: str) -> str:
        config = genai_types.GenerateContentConfig(
            temperature=0.4,
            top_p=0.9,
            max_output_tokens=1024,
            response_modalities=["TEXT"],
            safety_settings=[
                genai_types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH",       threshold="BLOCK_MEDIUM_AND_ABOVE"),
                genai_types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
                genai_types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
                genai_types.SafetySetting(category="HARM_CATEGORY_HARASSMENT",        threshold="BLOCK_MEDIUM_AND_ABOVE"),
            ],
        )
        contents = [
            genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=prompt)]
            )
        ]
        try:
            response = self._client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )
            return response.text or "No analysis returned."
        except Exception as e:
            return f"Gemini analysis failed: {e}\n\n{self._fallback_analysis({}, '')}"

    def _fallback_analysis(self, data: Dict, address: str) -> str:
        risk = data.get("risk_score", {})
        score = risk.get("overall", 0)
        label = risk.get("overall_label", "Unknown")
        crime_count = data.get("crime", {}).get("total_count", 0)

        return f"""
### Overall Assessment
**Risk Level: {label} ({score}/100)**
This analysis is based on {crime_count} crime incidents in the past 30 days,
current weather conditions, and 311 infrastructure reports.
Set up your `GOOGLE_AI_API_KEY` or configure Vertex AI for full AI-powered analysis.

### Crime Intelligence
- {crime_count} incidents recorded in the last 30 days
- Review the crime breakdown panel for type distribution
- Remain aware of surroundings, especially after dark

### Weather & Environmental
- Check the weather panel for current NWS alerts
- Monitor weather.gov for updates

### Infrastructure Status
- Review 311 panel for active complaints in your area

### Recommended Actions
1. Review crime type breakdown and adjust routines accordingly
2. Sign up for local NWS weather alerts at weather.gov
3. Report infrastructure issues via your city's 311 app
4. Know the location of your nearest emergency services
5. Stay informed via local news and Nextdoor
"""