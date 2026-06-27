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

        /* ── Agent Orchestration Map ─────────────────────────────────────────── */
        .amap {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 1.5rem 1.5rem 1.9rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(15,23,42,0.03), 0 1px 2px rgba(15,23,42,0.05);
        }
        .amap-head { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.9rem; }
        .amap-spark {
            width: 26px; height: 26px; border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            background: linear-gradient(135deg, var(--green), var(--blue));
            color: #fff; box-shadow: 0 2px 8px rgba(59,130,246,0.25);
        }
        .amap-spark svg { width: 15px; height: 15px; }
        .amap-title { font-family: var(--font-display); font-weight: 700; font-size: 1rem; color: var(--white); }
        .amap-counts { margin-left: auto; font-family: var(--font-mono); font-size: 0.8rem; color: var(--muted); }
        .amap-counts b { color: var(--green-dim); font-weight: 700; }
        .amap-bar { height: 8px; background: var(--bg-hover); border-radius: 99px; overflow: hidden; }
        .amap-bar-fill {
            height: 100%; border-radius: 99px;
            background: linear-gradient(90deg, var(--green), var(--blue));
            box-shadow: 0 0 10px rgba(16,185,129,0.45);
            transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .amap-sub {
            font-family: var(--font-mono); font-size: 0.68rem; color: var(--muted);
            letter-spacing: 0.05em; margin: 0.5rem 0 1.4rem;
        }
        .amap-flow { display: flex; flex-direction: column; align-items: center; }
        .amap-stage { display: flex; justify-content: center; flex-wrap: wrap; gap: 0.7rem; }
        .amap-stage.parallel {
            position: relative; padding: 1.1rem 0.9rem 0.9rem;
            border: 1px dashed var(--border); border-radius: var(--radius-md);
            background: rgba(59,130,246,0.018);
        }
        .amap-tag {
            position: absolute; top: -9px; left: 50%; transform: translateX(-50%);
            background: var(--bg-card); padding: 0 10px;
            font-family: var(--font-mono); font-size: 0.58rem; letter-spacing: 0.14em;
            text-transform: uppercase; color: var(--muted); white-space: nowrap;
        }
        .amap-link { width: 2px; height: 26px; border-radius: 2px; background: var(--border); }
        .amap-link.is-done { background: var(--green); opacity: 0.45; }
        .amap-link.is-active {
            background: linear-gradient(180deg, var(--blue) 0%, rgba(59,130,246,0) 70%);
            background-size: 100% 200%; animation: amapflow 1s linear infinite;
        }
        @keyframes amapflow { 0% { background-position: 0 -26px; } 100% { background-position: 0 26px; } }
        .amap-node {
            display: flex; flex-direction: column; align-items: center; gap: 0.35rem;
            width: 98px; padding: 0.6rem 0.3rem;
            border: 1px solid var(--border); border-radius: var(--radius-md);
            background: var(--bg-panel); transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .amap-node:hover { transform: translateY(-3px); box-shadow: 0 10px 18px rgba(15,23,42,0.08); border-color: var(--border-glow); }
        .amap-ico-wrap { position: relative; }
        .amap-ico {
            width: 40px; height: 40px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            border: 2px solid var(--border); color: var(--muted);
            background: var(--bg-card); transition: all 0.3s;
        }
        .amap-ico svg { width: 21px; height: 21px; }
        .amap-badge {
            position: absolute; right: -3px; bottom: -3px;
            width: 16px; height: 16px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            border: 2px solid var(--bg-panel); color: #fff;
        }
        .amap-badge svg { width: 9px; height: 9px; }
        .amap-spin2 {
            width: 8px; height: 8px; border: 2px solid rgba(255,255,255,0.55);
            border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite;
        }
        .amap-name { font-size: 0.72rem; font-weight: 600; color: var(--white); text-align: center; line-height: 1.15; }
        .amap-status { font-family: var(--font-mono); font-size: 0.56rem; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 700; color: var(--muted); }
        .amap-time { font-family: var(--font-mono); font-size: 0.6rem; color: var(--muted); min-height: 0.8rem; }
        .amap-err { font-size: 0.58rem; color: var(--red-dim); text-align: center; line-height: 1.2; }
        .amap-node.is-queued { opacity: 0.65; }
        .amap-node.is-running { border-color: var(--blue); }
        .amap-node.is-running .amap-ico { border-color: var(--blue); color: var(--blue-dim); animation: amapring 1.5s ease-in-out infinite; }
        .amap-node.is-running .amap-status { color: var(--blue-dim); }
        .amap-node.is-running .amap-badge { background: var(--blue); }
        .amap-node.is-done .amap-ico { border-color: var(--green); color: var(--green-dim); background: var(--green-bg); }
        .amap-node.is-done .amap-status { color: var(--green-dim); }
        .amap-node.is-done .amap-badge { background: var(--green); }
        .amap-node.is-failed { border-color: rgba(239,68,68,0.4); }
        .amap-node.is-failed .amap-ico { border-color: var(--red); color: var(--red-dim); background: var(--red-bg); }
        .amap-node.is-failed .amap-status { color: var(--red-dim); }
        .amap-node.is-failed .amap-badge { background: var(--red); }
        @keyframes amapring {
            0%, 100% { box-shadow: 0 0 0 0 rgba(59,130,246,0.4); }
            50%      { box-shadow: 0 0 0 7px rgba(59,130,246,0); }
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
    "infra": "311 Infra",
    "earthquakes": "Seismic",
    "risk": "Risk Scoring",
    "ai_briefing": "AI Briefing",
}


def _svg(inner: str) -> str:
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{inner}</svg>'
    )


_AGENT_ICONS = {
    "geocode": _svg('<path d="M12 21s-6-5.3-6-10a6 6 0 1 1 12 0c0 4.7-6 10-6 10z"/><circle cx="12" cy="11" r="2.3"/>'),
    "weather": _svg('<path d="M7 18a4 4 0 0 1 .6-8 5 5 0 0 1 9.5 1.3A3.5 3.5 0 0 1 17 18H7z"/>'),
    "nws": _svg('<path d="M12 4l9 16H3z"/><line x1="12" y1="10" x2="12" y2="14"/><circle cx="12" cy="17" r="0.6" fill="currentColor"/>'),
    "crime": _svg('<path d="M12 3l7 3v5c0 4.5-3 7.6-7 9-4-1.4-7-4.5-7-9V6z"/>'),
    "infra": _svg('<path d="M5 8l7-4 7 4"/><rect x="6" y="8" width="12" height="12" rx="1"/><path d="M10 20v-4h4v4"/>'),
    "earthquakes": _svg('<path d="M3 12h3l2-6 4 12 2-6h7"/>'),
    "risk": _svg('<path d="M5 18a7 7 0 1 1 14 0"/><line x1="12" y1="16" x2="15.5" y2="11.5"/>'),
    "ai_briefing": _svg('<path d="M12 3l1.7 4.3L18 9l-4.3 1.7L12 15l-1.7-4.3L6 9l4.3-1.7z"/><circle cx="18.5" cy="5.5" r="1" fill="currentColor"/>'),
}
_DEFAULT_ICON = _svg('<circle cx="12" cy="12" r="7"/>')

_BADGE = {
    "done": _svg('<path d="M5 13l4 4 10-11"/>'),
    "failed": _svg('<path d="M6 6l12 12M18 6L6 18"/>'),
    "running": '<span class="amap-spin2"></span>',
}

_SPARK = _svg('<path d="M12 3l1.7 4.3L18 9l-4.3 1.7L12 15l-1.7-4.3L6 9l4.3-1.7z"/>')


def _agent_depth(name: str, deps_map: Dict[str, List[str]], _cache: Dict[str, int]) -> int:
    if name in _cache:
        return _cache[name]
    deps = deps_map.get(name, [])
    depth = 0 if not deps else 1 + max(_agent_depth(d, deps_map, _cache) for d in deps)
    _cache[name] = depth
    return depth


def _fmt_elapsed(ms) -> str:
    if ms is None:
        return ""
    if ms < 1000:
        return f"{ms} ms"
    return f"{ms / 1000:.1f}s"


def _agent_node_html(row: Dict) -> str:
    name = row.get("name", "")
    status = row.get("status", "queued")
    if status not in ("queued", "running", "done", "failed"):
        status = "queued"
    label = _AGENT_LABELS.get(name, name.replace("_", " ").title())
    icon = _AGENT_ICONS.get(name, _DEFAULT_ICON)
    badge = f'<span class="amap-badge">{_BADGE[status]}</span>' if status in _BADGE else ""
    err = row.get("error")
    if status == "failed" and err:
        meta = f'<div class="amap-err">{_esc(err[:48])}</div>'
    else:
        meta = f'<div class="amap-time">{_esc(_fmt_elapsed(row.get("elapsed_ms")))}</div>'
    return (
        f'<div class="amap-node is-{status}">'
        f'<div class="amap-ico-wrap"><div class="amap-ico">{icon}</div>{badge}</div>'
        f'<div class="amap-name">{_esc(label)}</div>'
        f'<div class="amap-status">{_esc(status)}</div>'
        f'{meta}'
        '</div>'
    )


def _link_state(prev_stage: List[Dict], cur_stage: List[Dict]) -> str:
    cur = [n.get("status") for n in cur_stage]
    if cur and all(s == "done" for s in cur):
        return "is-done"
    prev_done = bool(prev_stage) and all(n.get("status") == "done" for n in prev_stage)
    if any(s == "running" for s in cur) or (prev_done and any(s in ("queued", "running") for s in cur)):
        return "is-active"
    return ""


def render_agent_trace(rows: List[Dict]):
    if not rows:
        rows = []

    deps_map = {r["name"]: r.get("deps", []) for r in rows}
    depth_cache: Dict[str, int] = {}

    stages: Dict[int, List[Dict]] = {}
    for r in rows:
        d = _agent_depth(r.get("name", ""), deps_map, depth_cache)
        stages.setdefault(d, []).append(r)
    ordered = [stages[d] for d in sorted(stages)]

    total = len(rows)
    done = sum(1 for r in rows if r.get("status") == "done")
    running = next((r for r in rows if r.get("status") == "running"), None)
    failed = sum(1 for r in rows if r.get("status") == "failed")
    pct = round(done / total * 100) if total else 0

    if running:
        sub = f'{pct}% · running {_esc(_AGENT_LABELS.get(running.get("name", ""), running.get("name", "")))}'
    elif total and done + failed == total:
        sub = "Pipeline complete" + (f' · {failed} degraded' if failed else "")
    else:
        sub = f"{pct}% complete"

    parts = [
        '<div class="amap">',
        '<div class="amap-head">'
        f'<span class="amap-spark">{_SPARK}</span>'
        '<span class="amap-title">Agent Orchestration</span>'
        f'<span class="amap-counts"><b>{_esc(done)}</b>/{_esc(total)} agents</span>'
        '</div>',
        f'<div class="amap-bar"><div class="amap-bar-fill" style="width:{pct}%"></div></div>',
        f'<div class="amap-sub">{sub}</div>',
        '<div class="amap-flow">',
    ]

    prev_stage = None
    for stage in ordered:
        if prev_stage is not None:
            parts.append(f'<div class="amap-link {_link_state(prev_stage, stage)}"></div>')
        parallel = len(stage) > 1
        cls = "amap-stage parallel" if parallel else "amap-stage"
        tag = f'<span class="amap-tag">{len(stage)} parallel agents</span>' if parallel else ""
        nodes = "".join(_agent_node_html(r) for r in stage)
        parts.append(f'<div class="{cls}">{tag}{nodes}</div>')
        prev_stage = stage

    parts.append("</div>")
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)



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