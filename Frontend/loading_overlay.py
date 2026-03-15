import html
import time

import streamlit as st


MIN_OVERLAY_SECONDS = 0.45


def show_loading_overlay(message: str):
    started_at = time.perf_counter()
    slot = st.empty()
    slot.markdown(
        f"""
        <style>
        .tay-loading-overlay {{
            position: fixed;
            inset: 0;
            z-index: 99998;
            display: flex;
            align-items: center;
            justify-content: center;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            background: rgba(248, 250, 252, 0.28);
            pointer-events: all;
        }}

        .tay-loading-card {{
            min-width: 220px;
            max-width: 320px;
            padding: 1rem 1.15rem;
            border-radius: 18px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 0.85rem;
            text-align: center;
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid rgba(148, 163, 184, 0.24);
            box-shadow: 0 20px 48px rgba(15, 23, 42, 0.16);
            box-sizing: border-box;
        }}

        .tay-loading-spinner {{
            display: block;
            width: 22px;
            height: 22px;
            border-radius: 999px;
            border: 3px solid rgba(148, 163, 184, 0.35);
            border-top-color: #2563eb;
            animation: tayLoadingSpin 0.85s linear infinite;
            flex: 0 0 auto;
            margin: 0 auto;
        }}

        .tay-loading-text {{
            width: 100%;
            color: #0f172a;
            font-size: 0.98rem;
            font-weight: 600;
            line-height: 1.35;
        }}

        @keyframes tayLoadingSpin {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}
        </style>
        <div class="tay-loading-overlay">
            <div class="tay-loading-card">
                <div class="tay-loading-spinner"></div>
                <div class="tay-loading-text">{html.escape(message)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return slot, started_at


def clear_loading_overlay(slot, started_at: float, minimum_seconds: float = MIN_OVERLAY_SECONDS):
    remaining = minimum_seconds - (time.perf_counter() - started_at)
    if remaining > 0:
        time.sleep(remaining)
    slot.empty()


def render_panel_loading(message: str, min_height_px: int = 180):
    st.markdown(
        f"""
        <style>
        div[data-testid="stMarkdownContainer"]:has(.tay-panel-loading) {{
            width: 100%;
        }}

        div[data-testid="stMarkdownContainer"]:has(.tay-panel-loading) > p {{
            margin: 0;
        }}

        .tay-panel-loading {{
            position: relative;
            width: 100%;
            height: {min_height_px}px;
            min-height: {min_height_px}px;
            border-radius: 18px;
            overflow: hidden;
            display: flex;
            align-items: stretch;
            justify-content: stretch;
            box-sizing: border-box;
            background:
                linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(241, 245, 249, 0.92));
            border: 1px solid rgba(148, 163, 184, 0.18);
        }}

        .tay-panel-loading::before {{
            content: '';
            position: absolute;
            inset: 0;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.28);
        }}

        .tay-panel-loading__content {{
            position: relative;
            z-index: 1;
            min-height: 100%;
            height: 100%;
            flex: 1 1 auto;
            width: 100%;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 0.8rem;
            padding: 1rem;
            text-align: center;
        }}

        .tay-panel-loading__spinner {{
            display: block;
            width: 28px;
            height: 28px;
            border-radius: 999px;
            border: 3px solid rgba(148, 163, 184, 0.35);
            border-top-color: #2563eb;
            animation: tayLoadingSpin 0.85s linear infinite;
            margin: 0 auto;
        }}

        .tay-panel-loading__text {{
            width: 100%;
            color: #334155;
            font-size: 0.96rem;
            font-weight: 600;
            line-height: 1.4;
        }}

        @keyframes tayLoadingSpin {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}
        </style>
        <div class="tay-panel-loading">
            <div class="tay-panel-loading__content">
                <div class="tay-panel-loading__spinner"></div>
                <div class="tay-panel-loading__text">{html.escape(message)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )