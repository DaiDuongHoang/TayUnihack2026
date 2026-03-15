import streamlit as st
from google.genai import Client
import html

from Authentication import is_authenticated, is_google_logged_in, is_guest, login_screen
from data_backend import get_user_catalog, get_user_location
from loading_overlay import show_loading_overlay, clear_loading_overlay
from openweatherapi import fetch_weather_bundle


TEMP_RANGES_BY_CLOTH_TYPE = {
    '👕 T-Shirt': (22, 40),
    '🧥 Hoodie': (10, 20),
    '🧥 Blazer': (15, 25),
    '🥼 Coat': (-5, 12),
    '🩲 Shorts': (25, 45),
    '👖 Jeans': (12, 28),
    '👖 Pants': (12, 28),
    '👗 Dress': (20, 35),
    '👗 Skirt': (20, 35),
    '🧶 Sweater': (8, 20),
    '🧥 Jacket': (8, 20),
}


def _load_user_catalog() -> dict[str, list[dict[str, object]]]:
    """Load wardrobe catalog from DB (local/Google) or session (guest)."""
    local_email = st.session_state.get('local_user')
    google_email = getattr(st.user, 'email', '') if is_google_logged_in() else ''
    user_email = local_email or google_email or None

    if 'catalog_owner' not in st.session_state:
        st.session_state.catalog_owner = None

    needs_refresh = (
        'catalog' not in st.session_state
        or st.session_state.catalog_owner != user_email
    )

    if needs_refresh:
        if user_email:
            try:
                st.session_state.catalog = get_user_catalog(user_email)
            except Exception:
                st.session_state.catalog = {}
        else:
            st.session_state.catalog = st.session_state.get('catalog', {})

        st.session_state.catalog_owner = user_email

    session_catalog = st.session_state.get('catalog')
    if isinstance(session_catalog, dict):
        return session_catalog

    return {}


def _flatten_catalog(
    catalog: dict[str, list[dict[str, object]]],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for category, entries in catalog.items():
        for entry in entries:
            if isinstance(entry, dict):
                items.append(
                    {
                        'name': str(entry.get('name', 'Unnamed Item')),
                        'cloth_type': str(entry.get('cloth_type') or 'Unknown Type'),
                        'color': str(entry.get('color') or 'Unknown Color'),
                        'category': str(category),
                    }
                )
            else:
                # Backward compatibility for tuple-style entries.
                name = str(entry[0]) if entry else 'Unnamed Item'
                items.append(
                    {
                        'name': name,
                        'cloth_type': 'Unknown Type',
                        'color': 'Unknown Color',
                        'category': str(category),
                    }
                )
    return items


def _wardrobe_context_text(items: list[dict[str, str]]) -> str:
    if not items:
        return 'Wardrobe is empty.'

    lines = []
    for item in items:
        lines.append(
            f'- {item["name"]} | type: {item["cloth_type"]} | color: {item["color"]} | category: {item["category"]}'
        )
    return '\n'.join(lines)


def _location_context_text() -> str:
    city, country = _resolve_location()
    if city and country:
        return f'Location: {city}, {country}'
    if city:
        return f'Location: {city}'
    if country:
        return f'Location: {country}'
    return 'Location unknown.'


def _resolve_location() -> tuple[str, str]:
    # First preference: same session keys used by the Weather page.
    saved_city = str(st.session_state.get('saved_city', '')).strip()
    saved_country = str(st.session_state.get('saved_country', '')).strip()

    if saved_city.lower() in {'n/a', 'na', 'none', 'null'}:
        saved_city = ''
    if saved_country.lower() in {'n/a', 'na', 'none', 'null'}:
        saved_country = ''

    if saved_city or saved_country:
        return saved_city, saved_country

    # Fallback: load persisted location for authenticated users.
    local_email = st.session_state.get('local_user')
    google_email = getattr(st.user, 'email', '') if is_google_logged_in() else ''
    user_email = local_email or google_email
    if not user_email:
        return '', ''

    try:
        loc = get_user_location(user_email)
        if not loc:
            return '', ''
        return str(loc.get('city', '')).strip(), str(loc.get('country', '')).strip()
    except Exception:
        return '', ''


def _get_live_weather_snapshot() -> dict[str, str]:
    city, country = _resolve_location()
    if not city and not country:
        return {}

    locality = city or country
    country_arg = country if city else ''
    try:
        bundle = fetch_weather_bundle(locality, country_arg)
        current = bundle.get('current', {})
        main = current.get('main', {})
        weather = (current.get('weather') or [{}])[0]
        wind = current.get('wind', {})
        return {
            'location': bundle.get('location') or f'{city}, {country}'.strip(', '),
            'temp_c': str(main.get('temp', 'N/A')),
            'humidity': str(main.get('humidity', 'N/A')),
            'description': str(weather.get('description', 'Unknown')),
            'wind_ms': str(wind.get('speed', 'N/A')),
        }
    except Exception:
        return {}


def _weather_context_text() -> str:
    snapshot = _get_live_weather_snapshot()
    if snapshot:
        return (
            f'Current weather in {snapshot["location"]}: '
            f'{snapshot["temp_c"]}C, {snapshot["description"]}, '
            f'humidity {snapshot["humidity"]}%, wind {snapshot["wind_ms"]} m/s.'
        )

    city, country = _resolve_location()
    if city and country:
        return f'Weather unavailable right now. Location context: {city}, {country}.'
    if city or country:
        return f'Weather unavailable right now. Location context: {city or country}.'
    return 'Weather unknown.'


def _get_current_temp_c() -> float | None:
    snapshot = _get_live_weather_snapshot()
    temp = snapshot.get('temp_c') if snapshot else None
    if temp in (None, 'N/A', ''):
        return None
    try:
        return float(temp)
    except (TypeError, ValueError):
        return None


def _weather_appropriate_items(
    wardrobe_items: list[dict[str, str]], temp_c: float | None
) -> list[dict[str, str]]:
    if temp_c is None:
        return wardrobe_items

    filtered: list[dict[str, str]] = []
    unknown: list[dict[str, str]] = []

    for item in wardrobe_items:
        cloth_type = item.get('cloth_type', '')
        temp_range = TEMP_RANGES_BY_CLOTH_TYPE.get(cloth_type)
        if temp_range is None:
            unknown.append(item)
            continue

        min_t, max_t = temp_range
        if min_t <= temp_c <= max_t:
            filtered.append(item)

    # Include unknown-type items as optional fallbacks.
    return filtered + unknown


def get_clothing_suggestion(
    user_input: str, wardrobe_items: list[dict[str, str]]
) -> str:
    api_key = 'AIzaSyDRrl6pMk2CBg6ujv6c3ieqBvE82nYOmNA'
    if not api_key:
        return 'Gemini API key is missing. Add GEMINI_API_KEY in Streamlit secrets.'

    client = Client(api_key=api_key)

    system_instruction = """
You are Taylr, a wardrobe assistant.
Rules:
1) Give outfit suggestions only using items from the provided wardrobe context.
2) If user asks for unavailable items, suggest the closest alternatives from wardrobe.
3) Keep responses concise and practical (2-5 bullet points).
4) Include one complete outfit when possible: Top + Bottom + optional Outerwear/Accessories.
5) If wardrobe is empty, ask user to add items first.
6) Respect weather strictly. Do not suggest warm-weather-only items when temperature is very cold.
"""

    current_temp_c = _get_current_temp_c()
    weather_items = _weather_appropriate_items(wardrobe_items, current_temp_c)
    if not weather_items and wardrobe_items:
        weather_items = wardrobe_items

    prompt = (
        f'{system_instruction}\n\n'
        f'User Profile: {"Guest user" if is_guest() else "Signed-in user"}\n'
        f'{_location_context_text()}\n\n'
        f'{_weather_context_text()}\n\n'
        f'Current Temp (C): {current_temp_c if current_temp_c is not None else "Unknown"}\n\n'
        f'Weather-Appropriate Wardrobe Context:\n{_wardrobe_context_text(weather_items)}\n\n'
        f'Full Wardrobe Context (fallback only):\n{_wardrobe_context_text(wardrobe_items)}\n\n'
        f'User Request: {user_input}\n'
        'Assistant:'
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite', contents=prompt
        )
        return (
            response.text or ''
        ).strip() or 'No suggestion generated. Please try again.'
    except Exception as exc:
        return f'Could not generate suggestions right now: {exc}'


def _render_suggestion_flow(text: str) -> None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        st.markdown(text)
        return

    rendered_lines = []
    for idx, line in enumerate(lines):
        cleaned = line.strip()

        # Normalize markdown-like emphasis markers from Gemini output.
        while cleaned.startswith('*'):
            cleaned = cleaned[1:].strip()
        while cleaned.endswith('*'):
            cleaned = cleaned[:-1].strip()
        cleaned = cleaned.replace('**', '').strip()

        if not cleaned:
            continue

        if cleaned.endswith(':') and ':' not in cleaned[:-1]:
            rendered_lines.append(
                f'<div class="ai-flow-section" style="animation-delay:{0.08 * idx:.2f}s">{html.escape(cleaned[:-1])}</div>'
            )
            continue

        if ':' in cleaned:
            label, value = cleaned.split(':', 1)
            label = html.escape(label.strip())
            value = html.escape(value.strip())
            rendered_lines.append(
                f'<div class="ai-flow-item" style="animation-delay:{0.08 * idx:.2f}s"><span class="ai-flow-label">{label}</span><span class="ai-flow-value">{value}</span></div>'
            )
            continue

        rendered_lines.append(
            f'<div class="ai-flow-line" style="animation-delay:{0.08 * idx:.2f}s">{html.escape(cleaned)}</div>'
        )

    st.markdown(
        '<div class="ai-flow-card"><div class="ai-flow-header">🪄 Suggested Looks</div>'
        + ''.join(rendered_lines)
        + '</div>',
        unsafe_allow_html=True,
    )


if not is_authenticated():
    login_screen(
        title='Sign in for wardrobe suggestions',
        description='Log in to get AI suggestions based on your wardrobe items.',
    )
    st.stop()

st.markdown(
    """
    <style>
    @keyframes aiFadeUp {
        from { opacity: 0; transform: translateY(18px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .ai-hero {
        border-radius: 20px;
        padding: 1.2rem 1.25rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(148, 163, 184, 0.25);
        background:
            radial-gradient(circle at 10% 20%, rgba(255, 243, 205, 0.65), transparent 45%),
            radial-gradient(circle at 90% 10%, rgba(186, 230, 253, 0.62), transparent 42%),
            linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.97));
        box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
        animation: aiFadeUp 0.55s ease-out both;
    }

    .ai-hero h2 {
        margin: 0;
        color: #0f172a;
        font-size: 1.65rem;
        line-height: 1.15;
    }

    .ai-hero p {
        margin: 0.5rem 0 0;
        color: #475569;
    }

    .ai-icon-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.8rem;
    }

    .ai-chip {
        border: 1px solid rgba(148, 163, 184, 0.3);
        border-radius: 999px;
        padding: 0.22rem 0.58rem;
        font-size: 0.78rem;
        color: #334155;
        background: rgba(255, 255, 255, 0.9);
    }

    .ai-stat {
        border-radius: 12px;
        border: 1px solid rgba(148, 163, 184, 0.25);
        background: rgba(255, 255, 255, 0.92);
        padding: 0.48rem 0.65rem;
        color: #334155;
        font-size: 0.88rem;
        margin-top: 0.35rem;
    }

    @keyframes aiFlowIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes aiTextShimmer {
        0% { background-position: 0% 50%; }
        100% { background-position: 100% 50%; }
    }

    .ai-flow-card {
        margin-top: 0.65rem;
        padding: 1rem 1rem 0.85rem;
        border-radius: 18px;
        border: 1px solid rgba(148, 163, 184, 0.22);
        background:
            radial-gradient(circle at 8% 10%, rgba(219, 234, 254, 0.7), transparent 38%),
            linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.98));
        box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
        overflow: hidden;
    }

    .ai-flow-header {
        font-size: 1rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.65rem;
    }

    .ai-flow-line {
        opacity: 0;
        animation: aiFlowIn 0.45s ease-out forwards;
        margin-bottom: 0.52rem;
        line-height: 1.55;
        color: #1e293b;
        background: linear-gradient(90deg, #0f172a, #1d4ed8, #0f766e, #0f172a);
        background-size: 260% 260%;
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        animation-name: aiFlowIn, aiTextShimmer;
        animation-duration: 0.45s, 5.5s;
        animation-timing-function: ease-out, linear;
        animation-fill-mode: forwards, none;
        animation-iteration-count: 1, infinite;
    }

    .ai-flow-section {
        opacity: 0;
        animation: aiFlowIn 0.45s ease-out forwards;
        margin: 0.9rem 0 0.45rem;
        font-size: 1rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: 0.01em;
    }

    .ai-flow-item {
        opacity: 0;
        animation: aiFlowIn 0.45s ease-out forwards;
        margin-bottom: 0.48rem;
        padding: 0.55rem 0.7rem;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(191, 219, 254, 0.8);
        display: flex;
        align-items: baseline;
        gap: 0.45rem;
        flex-wrap: wrap;
    }

    .ai-flow-label {
        font-weight: 700;
        color: #1d4ed8;
    }

    .ai-flow-value {
        color: #0f172a;
    }

    .ai-flow-bullet::before {
        content: '✦ ';
        color: #1d4ed8;
        -webkit-text-fill-color: initial;
    }

    div[data-testid="stForm"],
    div[data-testid="stAlert"],
    div[data-testid="stVerticalBlock"] {
        animation: aiFadeUp 0.48s ease-out both;
    }

    div[data-testid="stButton"] button,
    div[data-testid="stFormSubmitButton"] button {
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }

    div[data-testid="stButton"] button:hover,
    div[data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 26px rgba(15, 23, 42, 0.16);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="ai-hero">
            <h2>✨ AI Stylist</h2>
      <p>Weather-aware outfit recommendations built from your own wardrobe.</p>
            <div class="ai-icon-row">
                <span class="ai-chip">👗 Wardrobe</span>
                <span class="ai-chip">🌦️ Weather</span>
                <span class="ai-chip">🧠 Gemini</span>
            </div>
    </div>
    """,
    unsafe_allow_html=True,
)

page_overlay_slot, page_overlay_started_at = show_loading_overlay(
    'Loading AI Stylist...'
)
try:
    catalog = _load_user_catalog()
    items = _flatten_catalog(catalog)
    temp_now = _get_current_temp_c()
    city, country = _resolve_location()
finally:
    clear_loading_overlay(page_overlay_slot, page_overlay_started_at)

st.caption(f'Loaded {len(items)} wardrobe item(s) for recommendations.')
st.markdown(
    f'<div class="ai-stat">🧺 Wardrobe items ready: <strong>{len(items)}</strong></div>',
    unsafe_allow_html=True,
)
if temp_now is not None:
    st.caption(f'Current detected temperature: {temp_now:.1f}C')
    st.markdown(
        f'<div class="ai-stat">🌡️ Current temperature context: <strong>{temp_now:.1f}C</strong></div>',
        unsafe_allow_html=True,
    )

if not city and not country:
    st.warning(
        'Location is not selected yet. AI Stylist can still suggest outfits, but weather-aware recommendations may be less accurate. Set your location on the Location page first.'
    )

quick_left, quick_mid, quick_right = st.columns(3)
if quick_left.button('💼 Work / Office Look', key='llm_q_work', width='stretch'):
    st.session_state.llm_prefill_prompt = (
        'Suggest a work-ready outfit using my wardrobe and current weather.'
    )
if quick_mid.button('🧢 Casual Weekend', key='llm_q_casual', width='stretch'):
    st.session_state.llm_prefill_prompt = (
        'Suggest a casual weekend outfit from my wardrobe for current weather.'
    )
if quick_right.button('🧥 Layering Plan', key='llm_q_layer', width='stretch'):
    st.session_state.llm_prefill_prompt = (
        'Suggest a layered outfit option from my wardrobe for current weather.'
    )

user_input = st.text_input(
    '**Ask for outfit suggestions:**',
    value=st.session_state.pop('llm_prefill_prompt', ''),
    placeholder='e.g. Suggest a smart-casual outfit for 20C weather',
)

if user_input:
    with st.spinner('Generating outfit suggestions...'):
        suggestion = get_clothing_suggestion(user_input, items)
    st.toast('Outfit suggestion ready ✨')
    _render_suggestion_flow(suggestion)
