"""
UI Components for NeighborhoodAlert.
Aesthetic: Dark tactical intelligence dashboard — inspired by cybersecurity
SIEM tools and emergency operations centers. Deep navy base, acid-green
accents for safe status, amber for moderate, red for critical.
Typography: IBM Plex Mono (data/numbers) + Syne (headings) + Inter (body).
"""

import html

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional


def _esc(val) -> str:
    """HTML-escape a value for safe interpolation into unsafe_allow_html blocks."""
    return html.escape(str(val))



def inject_custom_css():
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@300;400;500;600;700&display=swap" rel="stylesheet">

        <style>
        /* ── Reset & Base ──────────────────────────────────────────────────── */
        :root {
            --bg-deep:    #f8fafc; /* Beautiful soft slate gray */
            --bg-panel:   #ffffff; /* Clean white */
            --bg-card:    #ffffff; /* Clean white */
            --bg-hover:   #f1f5f9; /* Soft hover highlight */
            --border:     #e2e8f0; /* Soft slate border */
            --border-glow:#cbd5e1; /* Elegant focus/active border */

            --green:      #10b981; /* Emerald green */
            --green-dim:  #047857; /* Rich dark green for light theme readability */
            --green-bg:   rgba(16, 185, 129, 0.08); /* Soft green background */
            --amber:      #f59e0b; /* Vibrant amber */
            --amber-dim:  #b45309; /* Rich dark amber for light theme readability */
            --amber-bg:   rgba(245, 158, 11, 0.08); /* Soft amber background */
            --red:        #ef4444; /* Vibrant rose/red */
            --red-dim:    #b91c1c; /* Rich dark red for light theme readability */
            --red-bg:     rgba(239, 68, 68, 0.08); /* Soft red background */
            --blue:       #3b82f6; /* Modern tech blue */
            --blue-dim:   #1d4ed8; /* Rich dark blue for light theme readability */
            --blue-bg:    rgba(59, 130, 246, 0.08); /* Soft blue background */
            
            --white:      #0f172a; /* Deep slate-900: Used for body and default texts */
            --muted:      #64748b; /* Slate-500: Used for descriptions, subtexts */

            --font-display: 'Outfit', sans-serif;
            --font-body:    'Plus Jakarta Sans', sans-serif;
            --font-mono:    'JetBrains Mono', monospace;

            --radius-sm:  6px;
            --radius-md:  12px;
            --radius-lg:  18px;
        }

        html, body, [class*="css"] {
            font-family: var(--font-body);
            background-color: var(--bg-deep) !important;
            color: var(--white);
        }

        /* Streamlit chrome removal */
        #MainMenu, footer, header { visibility: hidden; }
        .block-container {
            padding: 0 2rem 4rem !important;
            max-width: 1600px !important;
        }
        .stApp { background-color: var(--bg-deep) !important; }

        /* ── Scrollbar ──────────────────────────────────────────────────────── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-deep); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--border-glow); }

        /* ── Header ─────────────────────────────────────────────────────────── */
        .na-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 2rem 0 1.5rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2.5rem;
        }
        .na-header-left { display: flex; align-items: center; gap: 1rem; }
        .na-logo {
            width: 44px; height: 44px;
            background: linear-gradient(135deg, var(--green), var(--blue));
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.4rem;
            box-shadow: 0 4px 12px rgba(59,130,246,0.2);
        }
        .na-brand {
            font-family: var(--font-display);
            font-size: 1.6rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: var(--white);
        }
        .na-brand span { color: var(--green); }
        .na-tagline {
            font-family: var(--font-mono);
            font-size: 0.72rem;
            color: var(--muted);
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin-top: 2px;
            font-weight: 500;
        }
        .na-live-badge {
            display: flex; align-items: center; gap: 8px;
            font-family: var(--font-mono);
            font-size: 0.72rem;
            color: var(--green-dim);
            background: var(--green-bg);
            border: 1px solid rgba(16,185,129,0.15);
            padding: 6px 14px;
            border-radius: 20px;
            letter-spacing: 0.08em;
            font-weight: 600;
            box-shadow: 0 1px 2px rgba(16,185,129,0.02);
        }
        .live-dot {
            width: 7px; height: 7px;
            background: var(--green);
            border-radius: 50%;
            animation: pulse-dot 2s infinite;
        }
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50%       { opacity: 0.4; transform: scale(0.7); }
        }

        /* ── Search ──────────────────────────────────────────────────────────── */
        .search-section { margin-bottom: 0.75rem; }

        .stTextInput > div > div > input {
            background: var(--bg-panel) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
            color: var(--white) !important;
            font-family: var(--font-body) !important;
            font-size: 1rem !important;
            padding: 0.85rem 1.2rem !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        .stTextInput > div > div > input:focus {
            border-color: var(--blue) !important;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
            outline: none !important;
        }
        .stTextInput > div > div > input::placeholder { color: var(--muted) !important; }

        .stButton > button {
            background: linear-gradient(135deg, #10b981, #059669) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: var(--radius-md) !important;
            font-family: var(--font-display) !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            letter-spacing: 0.03em !important;
            padding: 0.7rem 1.4rem !important;
            box-shadow: 0 4px 12px rgba(16,185,129,0.18) !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            height: 100%;
        }
        .stButton > button:hover {
            opacity: 0.92 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 16px rgba(16,185,129,0.25) !important;
        }
        .stButton > button:active {
            transform: translateY(0) !important;
        }

        /* ── Chips ───────────────────────────────────────────────────────────── */
        .chip-row { margin-bottom: 2rem; }
        .chip-row .stButton > button {
            background: var(--bg-panel) !important;
            color: var(--muted) !important;
            border: 1px solid var(--border) !important;
            font-family: var(--font-mono) !important;
            font-size: 0.75rem !important;
            font-weight: 500 !important;
            padding: 0.3rem 0.8rem !important;
            border-radius: 20px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
            transition: all 0.15s ease !important;
        }
        .chip-row .stButton > button:hover {
            border-color: var(--blue) !important;
            color: var(--blue-dim) !important;
            background: var(--bg-hover) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.04) !important;
        }

        /* ── Alert Banner ────────────────────────────────────────────────────── */
        .alert-banner {
            border-radius: var(--radius-md);
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            border-left: 4px solid;
            box-shadow: 0 1px 3px rgba(15,23,42,0.03), 0 1px 2px rgba(15,23,42,0.05);
        }
        .alert-critical { background: var(--red-bg); border-color: var(--red); color: var(--red-dim); }
        .alert-high     { background: var(--amber-bg); border-color: var(--amber); color: var(--amber-dim); }
        .alert-moderate { background: var(--blue-bg); border-color: var(--blue); color: var(--blue-dim); }
        .alert-low      { background: var(--green-bg); border-color: var(--green); color: var(--green-dim); }

        .alert-label {
            font-family: var(--font-mono);
            font-size: 0.7rem;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            opacity: 0.8;
            font-weight: 600;
        }
        .alert-title {
            font-family: var(--font-display);
            font-size: 1.1rem;
            font-weight: 700;
        }

        /* ── KPI Row ─────────────────────────────────────────────────────────── */
        .kpi-row { margin-bottom: 1.5rem; }

        .kpi-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(15,23,42,0.03), 0 1px 2px rgba(15,23,42,0.05);
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            height: 100%;
        }
        .kpi-card:hover {
            border-color: var(--border-glow);
            transform: translateY(-2px);
            box-shadow: 0 10px 20px -3px rgba(15,23,42,0.06), 0 4px 6px -4px rgba(15,23,42,0.06);
        }
        .kpi-icon { font-size: 1.6rem; margin-bottom: 0.5rem; }
        .kpi-label {
            font-family: var(--font-mono);
            font-size: 0.68rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 0.5rem;
            font-weight: 600;
        }
        .kpi-value {
            font-family: var(--font-display);
            font-size: 1.8rem;
            font-weight: 800;
            line-height: 1.1;
        }
        .kpi-sub {
            font-size: 0.78rem;
            color: var(--muted);
            margin-top: 0.4rem;
            line-height: 1.4;
        }

        /* Risk gauge */
        .risk-gauge-wrap { text-align: center; }
        .risk-number {
            font-family: var(--font-display);
            font-size: 3.2rem;
            font-weight: 800;
            line-height: 1;
        }
        .risk-bar-bg {
            background: var(--bg-hover);
            border-radius: 6px;
            height: 8px;
            margin: 0.8rem 0 0.5rem;
            overflow: hidden;
        }
        .risk-bar-fill {
            height: 100%;
            border-radius: 6px;
            transition: width 1.2s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        .risk-label-text {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            font-weight: 700;
        }

        /* ── Panel Cards ─────────────────────────────────────────────────────── */
        .panel-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(15,23,42,0.03), 0 1px 2px rgba(15,23,42,0.05);
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            height: 100%;
        }
        .panel-card:hover {
            border-color: var(--border-glow);
            transform: translateY(-2px);
            box-shadow: 0 10px 20px -3px rgba(15,23,42,0.06), 0 4px 6px -4px rgba(15,23,42,0.06);
        }
        .panel-header {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 1.4rem;
            padding-bottom: 0.8rem;
            border-bottom: 1px solid var(--border);
        }
        .panel-icon { font-size: 1.2rem; }
        .panel-title {
            font-family: var(--font-display);
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: var(--white);
        }
        .panel-count {
            margin-left: auto;
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--muted);
            background: var(--bg-hover);
            padding: 4px 10px;
            border-radius: 12px;
            font-weight: 500;
        }

        /* Crime type rows */
        .crime-row {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            margin-bottom: 0.7rem;
        }
        .crime-type-name {
            font-size: 0.85rem;
            font-weight: 500;
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            color: var(--white);
        }
        .crime-bar-wrap {
            flex: 2;
            background: var(--bg-hover);
            border-radius: 4px;
            height: 6px;
            overflow: hidden;
        }
        .crime-bar {
            height: 100%;
            border-radius: 4px;
            background: var(--red);
            transition: width 1s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        .crime-count {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--muted);
            min-width: 2rem;
            text-align: right;
            font-weight: 500;
        }

        /* Weather forecast row */
        .forecast-row {
            display: flex;
            gap: 0.5rem;
            overflow-x: auto;
            padding-bottom: 0.3rem;
        }
        .forecast-cell {
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 0.8rem 1rem;
            text-align: center;
            min-width: 85px;
            flex-shrink: 0;
            box-shadow: 0 1px 2px rgba(0,0,0,0.01);
            transition: all 0.2s ease;
        }
        .forecast-cell:hover {
            border-color: var(--border-glow);
            background: var(--bg-hover);
            transform: scale(1.02);
        }
        .forecast-dt {
            font-family: var(--font-mono);
            font-size: 0.65rem;
            color: var(--muted);
            margin-bottom: 0.3rem;
            font-weight: 500;
        }
        .forecast-temp {
            font-family: var(--font-display);
            font-size: 1.15rem;
            font-weight: 700;
        }
        .forecast-desc {
            font-size: 0.68rem;
            color: var(--muted);
            margin-top: 0.2rem;
        }
        .forecast-pop {
            font-family: var(--font-mono);
            font-size: 0.68rem;
            color: var(--blue-dim);
            margin-top: 0.2rem;
            font-weight: 500;
        }

        /* Infra category badge */
        .infra-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--bg-hover);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 6px 14px;
            font-size: 0.75rem;
            font-weight: 500;
            margin: 0 4px 6px 0;
            color: var(--white);
            transition: all 0.15s ease;
        }
        .infra-badge:hover {
            border-color: var(--border-glow);
            background: var(--bg-panel);
            transform: translateY(-1px);
        }
        .infra-count-badge {
            background: var(--amber);
            color: #ffffff;
            border-radius: 10px;
            padding: 1px 7px;
            font-family: var(--font-mono);
            font-size: 0.65rem;
            font-weight: 600;
        }

        /* NWS alert pill */
        .nws-alert {
            background: var(--amber-bg);
            border: 1px solid rgba(245,158,11,0.15);
            border-radius: var(--radius-sm);
            padding: 0.7rem 0.9rem;
            margin-bottom: 0.5rem;
        }
        .nws-event {
            font-family: var(--font-display);
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--amber-dim);
        }
        .nws-headline {
            font-size: 0.75rem;
            color: var(--muted);
            margin-top: 3px;
            line-height: 1.4;
        }

        /* ── Map Section ─────────────────────────────────────────────────────── */
        .map-wrapper {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(15,23,42,0.03), 0 1px 2px rgba(15,23,42,0.05);
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        .map-wrapper:hover {
            border-color: var(--border-glow);
            box-shadow: 0 10px 20px -3px rgba(15,23,42,0.06), 0 4px 6px -4px rgba(15,23,42,0.06);
        }
        .map-header {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 1rem;
        }

        /* ── AI Analysis ─────────────────────────────────────────────────────── */
        .ai-card {
            background: linear-gradient(135deg, #ffffff 0%, rgba(59,130,246,0.02) 100%);
            border: 1px solid rgba(59,130,246,0.15);
            border-radius: var(--radius-lg);
            padding: 2rem;
            margin-top: 1.5rem;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(59,130,246,0.04), 0 2px 4px -1px rgba(59,130,246,0.02);
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        .ai-card:hover {
            border-color: rgba(59,130,246,0.3);
            box-shadow: 0 10px 20px -3px rgba(59,130,246,0.08), 0 4px 6px -4px rgba(59,130,246,0.08);
        }
        .ai-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--green), var(--blue), transparent);
        }
        .ai-header {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            margin-bottom: 1.5rem;
        }
        .ai-gem {
            width: 32px; height: 32px;
            background: linear-gradient(135deg, var(--green), var(--blue));
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1rem;
            color: #ffffff;
            box-shadow: 0 2px 8px rgba(59,130,246,0.2);
        }
        .ai-title {
            font-family: var(--font-display);
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--white);
        }
        .ai-model {
            font-family: var(--font-mono);
            font-size: 0.65rem;
            color: var(--blue-dim);
            letter-spacing: 0.1em;
            text-transform: uppercase;
            font-weight: 600;
        }
        .ai-content h3 {
            font-family: var(--font-display) !important;
            font-size: 1rem !important;
            font-weight: 700 !important;
            margin: 1.4rem 0 0.6rem !important;
            color: var(--white) !important;
        }
        .ai-content p, .ai-content li {
            font-size: 0.87rem !important;
            line-height: 1.7 !important;
            color: #334155 !important;
        }
        .ai-content ul { padding-left: 1.2rem !important; }

        /* ── Loading ─────────────────────────────────────────────────────────── */
        .loading-screen {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 4rem 0;
            gap: 1rem;
        }
        .loading-ring {
            width: 48px; height: 48px;
            border: 3px solid var(--border);
            border-top-color: var(--blue);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading-text {
            font-family: var(--font-display);
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--white);
        }
        .loading-sub {
            font-family: var(--font-mono);
            font-size: 0.72rem;
            color: var(--muted);
            letter-spacing: 0.1em;
            font-weight: 500;
        }

        /* ── Agent Orchestration Trace ───────────────────────────────────────── */
        .agent-trace {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(15,23,42,0.03), 0 1px 2px rgba(15,23,42,0.05);
        }
        .agent-trace-header {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 1.2rem;
            padding-bottom: 0.8rem;
            border-bottom: 1px solid var(--border);
        }
        .agent-trace-title {
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 1rem;
            color: var(--white);
        }
        .agent-trace-sub {
            font-family: var(--font-mono);
            font-size: 0.7rem;
            color: var(--muted);
            margin-left: auto;
            letter-spacing: 0.06em;
        }
        .agent-row {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            padding: 0.45rem 0;
            font-family: var(--font-mono);
            font-size: 0.8rem;
        }
        .agent-row.depth-1 { padding-left: 1.6rem; }
        .agent-row.depth-2 { padding-left: 3.2rem; }
        .agent-tree { color: var(--muted); opacity: 0.6; }
        .agent-name { color: var(--white); font-weight: 600; min-width: 120px; }
        .agent-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .agent-pill.queued  { background: var(--bg-hover); color: var(--muted); }
        .agent-pill.running { background: var(--blue-bg);  color: var(--blue-dim); }
        .agent-pill.done    { background: var(--green-bg); color: var(--green-dim); }
        .agent-pill.failed  { background: var(--red-bg);   color: var(--red-dim); }
        .agent-spin {
            width: 10px; height: 10px;
            border: 2px solid rgba(59,130,246,0.25);
            border-top-color: var(--blue);
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
        }
        .agent-elapsed {
            margin-left: auto;
            font-size: 0.7rem;
            color: var(--muted);
        }
        .agent-err {
            color: var(--red-dim);
            font-size: 0.7rem;
            font-style: italic;
        }

        /* ── Landing Hero ────────────────────────────────────────────────────── */
        .landing-hero {
            text-align: center;
            padding: 3rem 2rem 4rem;
            max-width: 700px;
            margin: 0 auto;
        }
        .landing-icon { font-size: 4rem; margin-bottom: 1rem; }
        .landing-title {
            font-family: var(--font-display) !important;
            font-size: 2.5rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.03em !important;
            margin-bottom: 1.2rem !important;
            background: linear-gradient(135deg, #0f172a, #1e3a8a);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .landing-desc {
            font-size: 1.05rem;
            color: var(--muted);
            line-height: 1.7;
            margin-bottom: 2.5rem;
        }
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.8rem;
            max-width: 550px;
            margin: 0 auto;
        }
        .feature-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 1rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
            box-shadow: 0 1px 3px rgba(15,23,42,0.02), 0 1px 2px rgba(15,23,42,0.04);
            transition: all 0.2s ease;
        }
        .feature-card:hover {
            border-color: var(--border-glow);
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(15,23,42,0.06);
        }
        .feature-icon { font-size: 1.5rem; }
        .feature-label { font-size: 0.72rem; color: var(--muted); text-align: center; font-weight: 500; }

        /* ── Footer ──────────────────────────────────────────────────────────── */
        .na-footer {
            margin-top: 5rem;
            padding: 2rem 0;
            border-top: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 1rem;
        }
        .na-footer-left {
            font-family: var(--font-mono);
            font-size: 0.72rem;
            color: var(--muted);
            font-weight: 500;
        }
        .na-footer-right {
            font-family: var(--font-mono);
            font-size: 0.72rem;
            color: var(--muted);
            font-weight: 500;
        }
        .na-footer a {
            color: var(--blue-dim);
            text-decoration: none;
            font-weight: 600;
            transition: color 0.15s ease;
        }
        .na-footer a:hover {
            color: var(--blue);
            text-decoration: underline;
        }

        /* ── Streamlit component overrides ───────────────────────────────────── */
        .stMetric { background: transparent !important; }
        .stExpander {
            background: var(--bg-panel) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-sm) !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
        }
        div[data-testid="stExpander"] > div:first-child {
            background: var(--bg-panel) !important;
        }
        div[data-testid="stExpander"] p, div[data-testid="stExpander"] li {
            color: var(--white) !important;
        }
        .stDataFrame {
            background: var(--bg-panel) !important;
        }

        /* Column gap fix */
        div[data-testid="column"] { padding: 0 0.4rem !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )




def render_header():
    from datetime import datetime
    now = datetime.utcnow().strftime("%H:%M UTC")
    st.markdown(
        f"""
        <div class="na-header">
            <div class="na-header-left">
                <div class="na-logo"></div>
                <div>
                    <div class="na-brand">Neighborhood<span>Alert</span></div>
                    <div class="na-tagline">Real-Time Safety Intelligence Platform</div>
                </div>
            </div>
            <div class="na-live-badge">
                <div class="live-dot"></div>
                LIVE · {now}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_alert_banner(risk: Dict):
    label  = risk.get("overall_label", "Low")
    score  = risk.get("overall", 0)
    cls_map = {"Critical": "alert-critical", "High": "alert-high", "Moderate": "alert-moderate", "Low": "alert-low"}
    icon_map = {"Critical": "", "High": "", "Moderate": "", "Low": ""}
    cls  = cls_map.get(label, "alert-low")
    icon = icon_map.get(label, "")

    msg_map = {
        "Critical": "Immediate attention required — multiple high-severity risks detected.",
        "High":     "Elevated risk profile — stay informed and take precautions.",
        "Moderate": "Moderate risk level — standard awareness recommended.",
        "Low":      "Low risk environment — conditions are within normal parameters.",
    }

    st.markdown(
        f"""
        <div class="alert-banner {cls}">
            <div style="font-size:1.8rem">{icon}</div>
            <div>
                <div class="alert-label">Neighborhood Risk Assessment</div>
                <div class="alert-title">{_esc(label)} Risk — Score {_esc(score)}/100 &nbsp; {_esc(msg_map.get(label,""))}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_risk_score_card(score: int, label: str):
    color = _risk_color(score)
    st.markdown(
        f"""
        <div class="kpi-card risk-gauge-wrap">
            <div class="kpi-label">{_esc(label)}</div>
            <div class="risk-number" style="color:{color}">{_esc(score)}</div>
            <div class="risk-bar-bg">
                <div class="risk-bar-fill" style="width:{int(score)}%;background:{color}"></div>
            </div>
            <div class="risk-label-text" style="color:{color}">{_esc(_score_label(score))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(icon: str, label: str, value: str, score: Optional[int], subtitle: str = ""):
    color = _risk_color(score) if score is not None else "var(--blue-dim)"
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-icon">{_esc(icon)}</div>
            <div class="kpi-label">{_esc(label)}</div>
            <div class="kpi-value" style="color:{color}">{_esc(value)}</div>
            {f'<div class="kpi-sub">{_esc(subtitle)}</div>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_map_section(geo: Dict, crime_pts: List[Dict]):
    st.markdown('<div class="map-wrapper">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="map-header">
            <span style="font-size:1.2rem"></span>
            <span style="font-family:var(--font-display);font-weight:700;font-size:1rem">
                Incident Map
            </span>
            <span style="font-family:var(--font-mono);font-size:0.7rem;color:var(--muted);margin-left:auto">
                Last 30 days · Crime incidents
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    lat0, lon0 = geo.get("lat", 41.87), geo.get("lon", -87.63)

    if crime_pts:
        df = pd.DataFrame(crime_pts[:300])
        if "lat" in df.columns and "lon" in df.columns:
            df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
            df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
            df = df.dropna(subset=["lat", "lon"])
        else:
            df = pd.DataFrame([{"lat": lat0, "lon": lon0}])
            
        if df.empty:
            df = pd.DataFrame([{"lat": lat0, "lon": lon0}])
    else:
        df = pd.DataFrame([{"lat": lat0, "lon": lon0}])

    st.map(df, latitude="lat", longitude="lon", zoom=12, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)



def _render_fbi_summary(summary: Dict):
    agency = summary.get("agency_name", "Local agency")
    st.markdown(
        '<p style="font-size:0.8rem;color:var(--muted);margin-bottom:1rem">'
        "No incident-level feed for this city. Showing FBI Crime Data Explorer "
        f'annual totals for <strong style="color:var(--white)">{_esc(agency)}</strong>.</p>',
        unsafe_allow_html=True,
    )
    rows = []
    if "violent_crime" in summary:
        rows.append(("Violent crime", summary.get("violent_year"), summary["violent_crime"]))
    if "property_crime" in summary:
        rows.append(("Property crime", summary.get("property_year"), summary["property_crime"]))
    for label, year, count in rows:
        yr = f" ({year})" if year else ""
        shown = f"{count:,}" if isinstance(count, int) else count
        st.markdown(
            '<div style="display:flex;align-items:center;justify-content:space-between;'
            'padding:0.55rem 0;border-bottom:1px solid var(--border)">'
            f'<span style="font-size:0.85rem;color:var(--white);font-weight:500">{_esc(label)}{_esc(yr)}</span>'
            '<span style="font-family:var(--font-mono);font-size:0.95rem;color:var(--red-dim);font-weight:600">'
            f"{_esc(shown)}</span></div>",
            unsafe_allow_html=True,
        )


def render_crime_section(crime: Dict):
    total = crime.get("total_count", 0)
    types = crime.get("type_counts", {})
    period = crime.get("period_days", 30)

    st.markdown(
        f"""
        <div class="panel-card">
            <div class="panel-header">
                <span class="panel-icon"></span>
                <span class="panel-title">Crime Intelligence</span>
                <span class="panel-count">{_esc(total)} / {_esc(period)}d</span>
            </div>
        """,
        unsafe_allow_html=True,
    )

    if types:
        top = sorted(types.items(), key=lambda x: x[1], reverse=True)[:10]
        max_v = max(v for _, v in top) if top else 1
        for name, count in top:
            pct = int((count / max_v) * 100)
            st.markdown(
                f"""
                <div class="crime-row">
                    <div class="crime-type-name" title="{_esc(name)}">{_esc(name)}</div>
                    <div class="crime-bar-wrap">
                        <div class="crime-bar" style="width:{pct}%"></div>
                    </div>
                    <div class="crime-count">{_esc(count)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    elif crime.get("fbi_summary"):
        _render_fbi_summary(crime["fbi_summary"])
    else:
        st.markdown(
            '<p style="color:var(--muted);font-size:0.82rem;text-align:center;padding:1.5rem 0">'
            "No crime data — this city's Socrata feed may not be supported yet.</p>",
            unsafe_allow_html=True,
        )

    fbi = crime.get("fbi_stats", {})
    if fbi.get("note"):
        st.markdown(
            f'<p style="font-family:var(--font-mono);font-size:0.65rem;color:var(--muted);margin-top:0.8rem">'
            f'ℹ {_esc(fbi["note"])}</p>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)



def render_weather_section(weather: Dict):
    cur = weather.get("current", {})
    forecast = weather.get("forecast", [])
    alerts = weather.get("alerts", [])
    stub = weather.get("stub", False)

    st.markdown(
        f"""
        <div class="panel-card">
            <div class="panel-header">
                <span class="panel-icon"></span>
                <span class="panel-title">Weather & Alerts</span>
                <span class="panel-count">{"NWS" if not stub else "demo"}</span>
            </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1rem">
            <div class="forecast-cell">
                <div class="forecast-dt">Temp</div>
                <div class="forecast-temp" style="color:var(--blue-dim)">{_esc(cur.get("temp_f","--"))}°F</div>
            </div>
            <div class="forecast-cell">
                <div class="forecast-dt">Feels</div>
                <div class="forecast-temp">{_esc(cur.get("feels_like_f","--"))}°F</div>
            </div>
            <div class="forecast-cell">
                <div class="forecast-dt">Wind</div>
                <div class="forecast-temp" style="font-size:1rem">{_esc(cur.get("wind_mph","--"))}<span style="font-size:0.7rem"> mph</span></div>
            </div>
            <div class="forecast-cell">
                <div class="forecast-dt">Humidity</div>
                <div class="forecast-temp" style="font-size:1rem">{_esc(cur.get("humidity","--"))}<span style="font-size:0.7rem">%</span></div>
            </div>
            <div class="forecast-cell">
                <div class="forecast-dt">Visibility</div>
                <div class="forecast-temp" style="font-size:1rem">{_esc(cur.get("visibility_mi","--"))}<span style="font-size:0.7rem"> mi</span></div>
            </div>
        </div>
        <p style="font-size:0.8rem;color:var(--muted);margin-bottom:1rem">
            {_esc(cur.get("sunrise","--"))} &nbsp;·&nbsp; {_esc(cur.get("sunset","--"))}
            &nbsp;·&nbsp; {_esc(cur.get("description","--"))}
        </p>
        """,
        unsafe_allow_html=True,
    )

    if alerts:
        st.markdown('<div style="margin-bottom:0.8rem">', unsafe_allow_html=True)
        for a in alerts[:3]:
            sev_color = {"Extreme": "var(--red-dim)", "Severe": "var(--red-dim)", "Moderate": "var(--amber-dim)"}.get(
                a.get("severity", ""), "var(--blue-dim)"
            )
            st.markdown(
                f"""
                <div class="nws-alert">
                    <div class="nws-event" style="color:{sev_color}">
                         {_esc(a.get("event",""))} · {_esc(a.get("severity",""))}
                    </div>
                    <div class="nws-headline">{_esc(a.get("headline","")[:120])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    if forecast:
        st.markdown('<div class="forecast-row">', unsafe_allow_html=True)
        for f in forecast[:6]:
            dt = f.get("dt", "")[-8:-3] if len(f.get("dt","")) > 10 else f.get("dt","")
            pop_color = "var(--blue-dim)" if f.get("pop", 0) > 30 else "var(--muted)"
            st.markdown(
                f"""
                <div class="forecast-cell">
                    <div class="forecast-dt">{_esc(dt)}</div>
                    <div class="forecast-temp">{_esc(f.get("temp_f","--"))}°</div>
                    <div class="forecast-desc">{_esc(f.get("description","")[:12])}</div>
                    <div class="forecast-pop" style="color:{pop_color}">{_esc(f.get("pop",0))}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    if stub:
        st.markdown(
            '<p style="font-family:var(--font-mono);font-size:0.65rem;color:var(--muted);margin-top:0.8rem">'
            "ℹ Set OPENWEATHER_API_KEY for live data.</p>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)



def render_infrastructure_section(infra: Dict):
    total = infra.get("total", 0)
    cats  = infra.get("categories", {})

    st.markdown(
        f"""
        <div class="panel-card">
            <div class="panel-header">
                <span class="panel-icon"></span>
                <span class="panel-title">311 Infrastructure</span>
                <span class="panel-count">{_esc(total)} complaints</span>
            </div>
        """,
        unsafe_allow_html=True,
    )

    if cats:
        st.markdown('<div style="margin-bottom:0.8rem">', unsafe_allow_html=True)
        for cat, count in sorted(cats.items(), key=lambda x: x[1], reverse=True)[:12]:
            st.markdown(
                f"""
                <span class="infra-badge">
                    {_esc(cat[:30])}
                    <span class="infra-count-badge">{_esc(count)}</span>
                </span>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        top_cats = dict(sorted(cats.items(), key=lambda x: x[1], reverse=True)[:8])
        df = pd.DataFrame(list(top_cats.items()), columns=["Category", "Count"])
        st.bar_chart(df.set_index("Category"), color="#f5a623", height=180)
    else:
        st.markdown(
            '<p style="color:var(--muted);font-size:0.82rem;text-align:center;padding:1.5rem 0">'
            "No 311 data — this city's feed may not be supported yet.</p>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)



_AGENT_LABELS = {
    "geocode": "Geocode",
    "weather": "Weather",
    "nws": "NWS Alerts",
    "crime": "Crime",
    "infra": "311 Infrastructure",
    "earthquakes": "Seismic",
    "risk": "Risk Scoring",
    "ai_briefing": "AI Briefing",
}

_AGENT_PILL = {
    "queued":  ("queued",  "•"),
    "running": ("running", '<span class="agent-spin"></span>'),
    "done":    ("done",    ""),
    "failed":  ("failed",  ""),
}


def _agent_depth(name: str, deps_map: Dict[str, List[str]], _cache: Dict[str, int]) -> int:
    """Longest-path depth of a node in the DAG (capped at 2 for indentation)."""
    if name in _cache:
        return _cache[name]
    deps = deps_map.get(name, [])
    depth = 0 if not deps else 1 + max(_agent_depth(d, deps_map, _cache) for d in deps)
    _cache[name] = depth
    return depth


def render_agent_trace(rows: List[Dict]):
    """Render the live multi-agent orchestration DAG (one row per subagent).

    `rows` is the plain-dict list from orchestration.ProgressBoard.snapshot():
    each has name / deps / status / elapsed_ms / error.
    """
    if not rows:
        rows = []

    deps_map = {r["name"]: r.get("deps", []) for r in rows}
    depth_cache: Dict[str, int] = {}
    done = sum(1 for r in rows if r.get("status") == "done")

    st.markdown('<div class="agent-trace">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="agent-trace-header">
            <span style="font-size:1.1rem"></span>
            <span class="agent-trace-title">Agent Orchestration</span>
            <span class="agent-trace-sub">{_esc(done)}/{_esc(len(rows))} subagents complete</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for r in rows:
        name = r.get("name", "")
        status = r.get("status", "queued")
        pill_cls, glyph = _AGENT_PILL.get(status, ("queued", "•"))
        label = _AGENT_LABELS.get(name, name.replace("_", " ").title())
        depth = min(_agent_depth(name, deps_map, depth_cache), 2)
        elapsed = r.get("elapsed_ms")
        elapsed_html = (
            f'<span class="agent-elapsed">{_esc(elapsed)} ms</span>'
            if elapsed is not None else '<span class="agent-elapsed"></span>'
        )
        err = r.get("error")
        err_html = f'<span class="agent-err">· {_esc(err[:60])}</span>' if err else ""
        tree = '<span class="agent-tree">└─</span>' if depth else ""

        st.markdown(
            f"""
            <div class="agent-row depth-{depth}">
                {tree}
                <span class="agent-name">{_esc(label)}</span>
                <span class="agent-pill {pill_cls}">{(glyph + " ") if glyph else ""}{_esc(status)}</span>
                {err_html}
                {elapsed_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)



def render_ai_analysis(text: str, address: str):
    st.markdown(
        f"""
        <div class="ai-card">
            <div class="ai-header">
                <div class="ai-gem"></div>
                <div>
                    <div class="ai-title">AI Safety Briefing</div>
                    <div class="ai-model">Vertex AI</div>
                </div>
                <div style="margin-left:auto;font-family:var(--font-mono);font-size:0.65rem;color:var(--muted)">
                     {_esc(address[:40])}
                </div>
            </div>
            <div class="ai-content">
        """,
        unsafe_allow_html=True,
    )
    st.markdown(text, unsafe_allow_html=False)
    st.markdown("</div></div>", unsafe_allow_html=True)



def render_footer():
    from datetime import datetime
    st.markdown(
        f"""
        <div class="na-footer">
            <div class="na-footer-left">
                © {datetime.utcnow().year} NeighborhoodAlert &nbsp;·&nbsp;
                Data: Socrata · FBI CDE · NWS · USGS · OpenWeatherMap
            </div>
            <div class="na-footer-right">
                 For informational purposes only. Not a substitute for emergency services.
                &nbsp;·&nbsp; <a href="https://weather.gov" target="_blank">weather.gov</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def _risk_color(score: Optional[int]) -> str:
    if score is None:
        return "var(--blue-dim)"
    if score >= 75:
        return "var(--red-dim)"
    if score >= 50:
        return "var(--amber-dim)"
    if score >= 25:
        return "var(--blue-dim)"
    return "var(--green-dim)"


def _score_label(score: int) -> str:
    from utils.data_fetcher import DataFetcher
    return DataFetcher._score_label(score)