import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import time

from dotenv import load_dotenv
from utils.data_fetcher import DataFetcher
from utils.ai_analyzer import AIAnalyzer
from utils.orchestration import start_pipeline
from components.ui_components import (
    render_header,
    render_risk_score_card,
    render_metric_card,
    render_alert_banner,
    render_crime_section,
    render_weather_section,
    render_infrastructure_section,
    render_map_section,
    render_agent_trace,
    render_ai_analysis,
    render_footer,
    inject_custom_css,
)

load_dotenv()


st.set_page_config(
    page_title="NeighborhoodAlert — Real-Time Safety Intelligence",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_custom_css()


CACHE_TTL = 300
POLL_INTERVAL = 0.4


def _cache_get(address: str):
    entry = st.session_state.pipeline_cache.get(address)
    if not entry:
        return None
    data, ts = entry
    if time.time() - ts > CACHE_TTL:
        return None
    return data


def _cache_put(address: str, data: dict):
    st.session_state.pipeline_cache[address] = (data, time.time())


def initialize_session():
    if "analyzer" not in st.session_state:
        st.session_state.analyzer = AIAnalyzer()
    if "last_data" not in st.session_state:
        st.session_state.last_data = None
    if "last_address" not in st.session_state:
        st.session_state.last_address = ""
    if "pipeline_cache" not in st.session_state:
        st.session_state.pipeline_cache = {}
    if "board" not in st.session_state:
        st.session_state.board = None
    if "board_addr" not in st.session_state:
        st.session_state.board_addr = None

def _render_kpi_row(data):
    risk = data.get("risk_score", {})
    wdata = data.get("weather", {}).get("current", {})
    st.markdown('<div class="kpi-row">', unsafe_allow_html=True)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        render_risk_score_card(risk.get("overall", 0), "Overall Risk")
    with k2:
        render_metric_card("", "Crime Index", risk.get("crime_label", "N/A"), risk.get("crime_score", 0))
    with k3:
        render_metric_card("", "Weather Risk", risk.get("weather_label", "N/A"), risk.get("weather_score", 0))
    with k4:
        render_metric_card("", "Infrastructure", risk.get("infra_label", "N/A"), risk.get("infra_score", 0))
    with k5:
        render_metric_card("", "Temperature", f"{wdata.get('temp_f', '--')}°F", None, subtitle=wdata.get("description", ""))
    st.markdown('</div>', unsafe_allow_html=True)


def main():
    initialize_session()
    render_header()

    st.markdown('<div class="search-section">', unsafe_allow_html=True)
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        address = st.text_input(
            label="address",
            label_visibility="collapsed",
            placeholder="Enter a US address, city, or zip code…",
            value=st.session_state.last_address,
            key="address_input",
        )
    with col_btn:
        analyze = st.button("Analyze", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="chip-row">', unsafe_allow_html=True)
    examples = ["Chicago, IL", "Brooklyn, NY", "Los Angeles, CA", "Houston, TX", "Seattle, WA"]
    chip_cols = st.columns(len(examples))
    for col, example in zip(chip_cols, examples):
        with col:
            if st.button(example, key=f"chip_{example}", use_container_width=True):
                address = example
                analyze = True
    st.markdown('</div>', unsafe_allow_html=True)

    if analyze and address.strip():
        addr = address.strip()
        st.session_state.last_address = addr
    elif st.session_state.board_addr:
        addr = st.session_state.board_addr
    else:
        addr = None

    if addr:
        cached = _cache_get(addr)
        if cached is not None:
            st.session_state.last_data = cached
            st.session_state.board_addr = None
        else:
            if st.session_state.board_addr != addr:
                st.session_state.board = start_pipeline(addr, DataFetcher(), st.session_state.analyzer)
                st.session_state.board_addr = addr

            board = st.session_state.board
            render_agent_trace(board.snapshot())

            if not board.is_done():
                render_footer()
                time.sleep(POLL_INTERVAL)
                st.rerun()

            try:
                data = board.result()
            except Exception as e:
                st.session_state.board_addr = None
                st.error(f"Data fetch failed: {e}")
                render_footer()
                return

            _cache_put(addr, data)
            st.session_state.last_data = data
            st.session_state.board_addr = None

        _render_results(st.session_state.last_data, addr)

    elif st.session_state.last_data:
        _render_results(st.session_state.last_data, st.session_state.last_address)
    else:
        render_landing()

    render_footer()




def _render_results(data: dict, address: str):
    """Render the full dashboard from an assembled pipeline result."""
    if not data:
        st.error("No data returned for this location.")
        return

    render_alert_banner(data.get("risk_score", {}))
    _render_kpi_row(data)

    geo = data.get("geo", {})
    crime_pts = data.get("crime", {}).get("incidents", [])
    render_map_section(geo, crime_pts)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        render_crime_section(data.get("crime", {}))
    with col_b:
        render_weather_section(data.get("weather", {}))
    with col_c:
        render_infrastructure_section(data.get("infrastructure", {}))

    analysis = data.get("analysis")
    if analysis:
        render_ai_analysis(analysis, address)


def render_landing():
    st.markdown(
        """
        <div class="landing-hero">
            <div class="landing-icon"></div>
            <h2 class="landing-title">Real-time neighborhood intelligence</h2>
            <p class="landing-desc">
                NeighborhoodAlert aggregates crime reports, weather alerts, 311 infrastructure
                complaints, and seismic data — then runs them through an AI risk model
                to give you a single, actionable safety score for any US address.
            </p>
            <div class="feature-grid">
                <div class="feature-card">
                    <span class="feature-icon"></span>
                    <span class="feature-label">FBI + Socrata Crime Data</span>
                </div>
                <div class="feature-card">
                    <span class="feature-icon"></span>
                    <span class="feature-label">NWS Weather Alerts</span>
                </div>
                <div class="feature-card">
                    <span class="feature-icon"></span>
                    <span class="feature-label">311 Infrastructure Feed</span>
                </div>
                <div class="feature-card">
                    <span class="feature-icon"></span>
                    <span class="feature-label">USGS Seismic Data</span>
                </div>
                <div class="feature-card">
                    <span class="feature-icon"></span>
                    <span class="feature-label">Gemini AI Risk Model</span>
                </div>
                <div class="feature-card">
                    <span class="feature-icon"></span>
                    <span class="feature-label">Hyper-local Coverage</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()