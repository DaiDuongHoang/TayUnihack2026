import streamlit as st
from Authentication import is_authenticated, login_screen
import base64
import re
from pathlib import Path
from data_backend import get_user_location, get_user_catalog
from loading_overlay import (
    show_loading_overlay,
    clear_loading_overlay,
    render_panel_loading,
)
from openweatherapi import fetch_weather_bundle

try:
    import pycountry
except Exception:
    pycountry = None

# use wide layout so panels have more room
st.set_page_config(layout='wide')


CLOTH_TYPE_OPTIONS = [
    '👕 T-Shirt',
    '🧥 Blazer',
    '👗 Dress',
    '🧥 Jacket',
    '🥼 Coat',
    '🧥 Hoodie',
    '🧶 Sweater',
    '🩲 Shorts',
    '👗 Skirt',
    '👖 Jeans',
    '👖 Pants',
    '🧢 Hat',
    '🕶️ Sunglasses',
    '🧣 Scarf',
    '🧤 Gloves',
]

CATEGORY_BY_CLOTH_TYPE = {
    '👕 T-Shirt': 'Top 👚',
    '👗 Dress': 'Top 👚',
    '🧶 Sweater': 'Top 👚',
    '🩲 Shorts': 'Bottom 🩳',
    '👗 Skirt': 'Bottom 🩳',
    '👖 Jeans': 'Bottom 🩳',
    '👖 Pants': 'Bottom 🩳',
    '🧥 Blazer': 'Outerwear 🧥',
    '🧥 Jacket': 'Outerwear 🧥',
    '🥼 Coat': 'Outerwear 🧥',
    '🧥 Hoodie': 'Outerwear 🧥',
    '🧢 Hat': 'Accessories ⌚',
    '🕶️ Sunglasses': 'Accessories ⌚',
    '🧣 Scarf': 'Accessories ⌚',
    '🧤 Gloves': 'Accessories ⌚',
}


def _ensure_catalog_categories():
    if 'catalog' not in st.session_state:
        st.session_state.catalog = {}

    for category in ('Top 👚', 'Bottom 🩳', 'Outerwear 🧥', 'Accessories ⌚'):
        st.session_state.catalog.setdefault(category, [])


def _plain_cloth_type_name(cloth_type):
    return cloth_type.split(' ', 1)[1] if ' ' in cloth_type else cloth_type


def _add_item_to_catalog(name, cloth_type, image=None, color=None):
    _ensure_catalog_categories()
    category = CATEGORY_BY_CLOTH_TYPE.get(cloth_type, 'Accessories ⌚')
    st.session_state.catalog[category].append(
        {
            'name': name,
            'image': image,
            'color': color,
            'cloth_type': cloth_type,
        }
    )
    return category


def _description_emoji(description):
    desc = str(description or '').lower()
    if 'thunder' in desc:
        return '⛈️'
    if 'rain' in desc or 'drizzle' in desc:
        return '🌧️'
    if 'snow' in desc:
        return '❄️'
    if 'mist' in desc or 'fog' in desc or 'haze' in desc:
        return '🌫️'
    if 'overcast' in desc:
        return '☁️'
    if 'cloud' in desc:
        return '⛅'
    if 'clear' in desc:
        return '☀️'
    return '🌤️'


GUEST_ASSET_DIR = Path(__file__).resolve().parent / 'default_clothes_guest'
GUEST_DEFAULT_ITEMS = {
    'Top 👚': [
        {'name': 'White T-Shirt', 'asset': 'white t-shirt.png'},
        {'name': 'Blue Polo', 'asset': 'blue polo.png'},
        {'name': 'Striped Shirt', 'asset': 'stripped shirt.png'},
    ],
    'Bottom 🩳': [
        {'name': 'Chinos', 'asset': 'chinos.png'},
        {'name': 'Joggers', 'asset': 'joggers.png'},
        {'name': 'Jeans', 'asset': 'jeans.png'},
    ],
    'Outerwear 🧥': [
        {'name': 'Denim Jacket', 'asset': 'Denim jacket.png'},
        {'name': 'Trench Coat', 'asset': 'Trench coat.png'},
        {'name': 'Puffer Vest', 'asset': 'puffer vest.png'},
    ],
    'Accessories ⌚': [
        {'name': 'Leather Belt', 'asset': 'Leather belt.png'},
        {'name': 'Wool Scarf', 'asset': 'wool scarf.png'},
        {'name': 'Baseball Cap', 'asset': 'baseball cap.png'},
    ],
}


@st.cache_data(show_spinner=False)
def _load_guest_asset_bytes(file_name: str) -> bytes | None:
    asset_path = GUEST_ASSET_DIR / file_name
    if not asset_path.exists():
        return None
    return asset_path.read_bytes()


def _default_catalog() -> dict[str, list[dict[str, object]]]:
    catalog = {category: [] for category in GUEST_DEFAULT_ITEMS}
    for category, items in GUEST_DEFAULT_ITEMS.items():
        for item in items:
            catalog[category].append(
                {
                    'name': item['name'],
                    'image': _load_guest_asset_bytes(item['asset']),
                    'color': None,
                }
            )
    return catalog


def _catalog_has_any_items(catalog: object) -> bool:
    if not isinstance(catalog, dict):
        return False
    return any(bool(items) for items in catalog.values())


# Defining functions to display weather and wardrobe widgets


def _load_catalog_if_missing():
    local_email = st.session_state.get('local_user')
    google_email = (
        getattr(st.user, 'email', '') if getattr(st.user, 'is_logged_in', False) else ''
    )
    active_owner = local_email or google_email or None

    if 'catalog_owner' not in st.session_state:
        st.session_state.catalog_owner = None

    guest_catalog_empty = active_owner is None and not _catalog_has_any_items(
        st.session_state.get('catalog')
    )

    needs_refresh = (
        'catalog' not in st.session_state
        or st.session_state.catalog_owner != active_owner
        or guest_catalog_empty
    )

    if needs_refresh:
        if active_owner:
            try:
                st.session_state.catalog = get_user_catalog(active_owner)
            except Exception:
                st.session_state.catalog = {}
        else:
            st.session_state.catalog = _default_catalog()

        st.session_state.catalog_owner = active_owner


def _is_stale_media_id(value: object) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip().lower()
    return bool(re.fullmatch(r'[0-9a-f]{40,64}\.(jpg|jpeg|png|webp)', text))


def _display_wardrobe_preview():
    _load_catalog_if_missing()
    catalog = st.session_state.get('catalog', {})
    items = []
    for cat, entries in catalog.items():
        for it in entries:
            if isinstance(it, dict):
                items.append(
                    {
                        'name': it.get('name', 'Unnamed'),
                        'image': it.get('image'),
                        'color': it.get('color'),
                        'category': cat,
                    }
                )
            else:
                name, image = it
                items.append(
                    {'name': name, 'image': image, 'color': None, 'category': cat}
                )

    st.subheader('Wardrobe Preview')
    if not items:
        st.info('No wardrobe items available to preview.')
        return

    search_query = st.text_input(
        'Search wardrobe',
        key='dashboard_wardrobe_search',
        placeholder='Filter by name…',
        label_visibility='collapsed',
    )
    if search_query.strip():
        q = search_query.strip().lower()
        items = [it for it in items if q in it.get('name', '').lower()]
    if not items:
        st.info('No items match your search.')
        return

    per_row = 3
    for i in range(0, len(items), per_row):
        cols = st.columns(per_row, gap='small')
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(items):
                break
            item = items[idx]
            with col:
                name = item.get('name')
                img = item.get('image')
                if _is_stale_media_id(img):
                    img = None
                color = item.get('color')
                category = item.get('category')

                # prepare image or color block as HTML, wrapped in a uniform container
                img_html = ''
                if img:
                    try:
                        if isinstance(img, (bytes, bytearray)):
                            b64 = base64.b64encode(img).decode('utf-8')
                            img_html = f'<img class="wardrobe-img-el" src="data:image/png;base64,{b64}" style="width:100%;object-fit:cover;border-radius:8px;"/>'
                        else:
                            img_html = f'<img class="wardrobe-img-el" src="{img}" style="width:100%;object-fit:cover;border-radius:8px;"/>'
                    except Exception:
                        img_html = '<div class="wardrobe-img-placeholder" style="width:100%;display:flex;align-items:center;justify-content:center;background:#f3f4f6;border-radius:8px;">(image)</div>'
                elif color:
                    img_html = f'<div class="wardrobe-img-color" style="width:100%;border-radius:8px;background:{color};border:1px solid rgba(0,0,0,0.06);"></div>'

                # card layout: image is inside a container `wardrobe-img` so we can set a uniform height later
                card_html = f"""
                <div style="border-radius:12px;padding:10px;border:1px solid rgba(0,0,0,0.06);box-shadow:0 6px 18px rgba(0,0,0,0.06);">
                    <div style=\"font-weight:600;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;\">{name}</div>
                    <div class="wardrobe-img" style="width:100%;height:auto;overflow:hidden;border-radius:8px;">
                        {img_html}
                    </div>
                    <div style=\"margin-top:8px;color:#6b7280;font-size:0.9rem;\">{category}</div>
                </div>
                """

                st.markdown(card_html, unsafe_allow_html=True)

        # After rendering all cards, inject JS to measure image natural sizes and set a uniform height
        sizing_script = """
        <script>
        (function(){
            try{
                const imgs = Array.from(document.querySelectorAll('.wardrobe-img-el'));
                const containers = Array.from(document.querySelectorAll('.wardrobe-img'));
                if(!containers.length) return;

                let pending = imgs.length || 1;
                let maxH = 0;

                function finalize(){
                    if(maxH <= 0) return;
                    containers.forEach(c => { c.style.height = maxH + 'px'; });
                }

                function consider(img){
                    try{
                        const rectW = img.clientWidth || img.naturalWidth || 0;
                        const natW = img.naturalWidth || rectW;
                        const natH = img.naturalHeight || rectW;
                        const displayH = natW ? Math.round(natH * (rectW / natW)) : img.clientHeight || 0;
                        if(displayH > maxH) maxH = displayH;
                    }catch(e){}
                }

                imgs.forEach(img => {
                    if(img.complete && img.naturalWidth){
                        consider(img);
                        pending--;
                        if(pending === 0) finalize();
                    } else {
                        img.addEventListener('load', function(){ consider(img); pending--; if(pending===0) finalize(); });
                        img.addEventListener('error', function(){ pending--; if(pending===0) finalize(); });
                    }
                });

                // in case there are no img elements, still set containers to a sensible default
                if(imgs.length === 0){
                    const defaultH = 180;
                    containers.forEach(c => c.style.height = defaultH + 'px');
                }
            }catch(e){console.error(e);}
        })();
        </script>
        """

        st.markdown(sizing_script, unsafe_allow_html=True)


def _resolve_weather_location():
    # any authenticated email: local or Google
    user_email = st.session_state.get('local_user') or getattr(st.user, 'email', None)

    location = None
    if user_email:
        try:
            loc = get_user_location(user_email)
            city = (loc or {}).get('city', '').strip()
            country = (loc or {}).get('country', '').strip()
            if city or country:
                location = (city, country)
        except Exception:
            location = None
    else:
        # guest or unauthenticated: use any saved session values if present
        saved_country = st.session_state.get('saved_country', '')
        saved_city = st.session_state.get('saved_city', '')
        if saved_city or saved_country:
            location = (saved_city, saved_country)

    return location


def _to_country_code(country_name_or_code: str) -> str:
    country = str(country_name_or_code or '').strip()
    if not country:
        return ''

    if len(country) == 2 and country.isalpha():
        return country.upper()

    if pycountry is not None:
        try:
            return str(pycountry.countries.lookup(country).alpha_2).upper()
        except LookupError:
            pass

    # Fallback to original text and let OpenWeather geocoding resolve it.
    return country


def _load_weather_panel_state():
    location = _resolve_weather_location()
    if not location:
        return location, None, None

    try:
        city = str(location[0] or '').strip()
        country = str(location[1] or '').strip()

        if city:
            locality = city
            country_arg = _to_country_code(country) if country else ''
        else:
            locality = country
            country_arg = ''

        bundle = fetch_weather_bundle(locality, country_arg)
        return location, bundle, None
    except Exception as exc:
        return location, None, str(exc)


def _display_weather(location, bundle, error_message):
    if not location:
        # If no saved location, show a button that takes the user to the Location page
        if st.button(
            'Set location',
            width='stretch',
            key='go_to_location',
            type='primary',
        ):
            st.switch_page('location.py')
            try:
                st.experimental_set_query_params(page='Location')
            except Exception:
                pass
        st.info("No location provided. Click 'Set location' to open the Location page.")
        return

    if error_message:
        st.warning(f'Unable to fetch weather: {error_message}')
        return

    cur = bundle.get('current', {})
    main = cur.get('main', {})
    weather = cur.get('weather', [{}])[0]

    try:
        desc_text = (weather.get('main') or weather.get('description') or '').strip()
        emoji = _description_emoji(desc_text)
    except Exception:
        emoji = ''

    st.subheader(f'Weather Panel {emoji}')

    cols = st.columns([1, 2])
    with cols[0]:
        temp_val = main.get('temp', None)
        try:
            temp_text = f'{float(temp_val):.1f}'
        except Exception:
            temp_text = 'N/A'
        st.metric('Temp (°C)', temp_text)
        st.caption(bundle.get('location', ''))
    with cols[1]:
        st.markdown(f'**{weather.get("main", "")}** — {weather.get("description", "")}')
        st.write(f'**Humidity**: {main.get("humidity", "N/A")}%')
        st.write(f'**Wind**: {cur.get("wind", {}).get("speed", "N/A")} m/s')


def _display_ai_stylist_panel():
    st.subheader('AI Stylist')
    st.caption('Get an outfit recommendation using your current weather and wardrobe.')
    if st.button(
        'Suggest Outfit with AI',
        key='dashboard_ai_stylist',
        type='primary',
        width='stretch',
        icon='✨',
    ):
        overlay_slot, overlay_started_at = show_loading_overlay('Opening AI Stylist...')
        st.session_state.llm_prefill_prompt = (
            'Suggest an outfit based on my current weather and my wardrobe. '
            'Give one best outfit and one backup option.'
        )
        clear_loading_overlay(overlay_slot, overlay_started_at)
        st.switch_page('LLM.py')


# CSS animations
st.html("""
<style>
/* Slide-fade-DOWN keyframe */
@keyframes slideFadeDown {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Apply to all buttons */
div[data-testid="stButton"] button {
    animation: slideFadeDown 0.4s ease forwards;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

/* Apply to bordered column/grid boxes */
div[data-testid="stColumn"] {
    animation: slideFadeDown 0.4s ease forwards;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

/* Apply to horizontal divider */
div[data-testid="stDivider"] {
    animation: slideFadeDown 0.4s ease 0.3s forwards;
    opacity: 0; /* Start hidden until animation runs */
}

/* Stagger for buttons */
div[data-testid="stButton"]:nth-child(1) button { animation-delay: 0.0s; }
div[data-testid="stButton"]:nth-child(2) button { animation-delay: 0.1s; }
div[data-testid="stButton"]:nth-child(3) button { animation-delay: 0.2s; }
div[data-testid="stButton"]:nth-child(4) button { animation-delay: 0.3s; }

/* Stagger for grid boxes */
div[data-testid="stColumn"]:nth-child(1) { animation-delay: 0.0s; }
div[data-testid="stColumn"]:nth-child(2) { animation-delay: 0.1s; }
div[data-testid="stColumn"]:nth-child(3) { animation-delay: 0.2s; }
div[data-testid="stColumn"]:nth-child(4) { animation-delay: 0.3s; }

/* Keep hover effect on buttons */
div[data-testid="stButton"] button:hover {
    transform: translateY(-3px) scale(1.07);
    box-shadow: 0px 10px 22px rgba(0, 0, 0, 0.28);
}

/* Dedicated animation for the Go Back button */
@keyframes backButtonFloat {
    0%,
    100% {
        transform: translateY(0);
    }
    50% {
        transform: translateY(-7px);
    }
}

@keyframes backButtonWiggle {
    0% {
        transform: translateX(-6px) scale(1.09) rotate(0deg);
    }
    25% {
        transform: translateX(-10px) scale(1.11) rotate(-2deg);
    }
    50% {
        transform: translateX(-6px) scale(1.12) rotate(2deg);
    }
    75% {
        transform: translateX(-10px) scale(1.11) rotate(-1deg);
    }
    100% {
        transform: translateX(-6px) scale(1.09) rotate(0deg);
    }
}

.st-key-back_button button {
    animation: backButtonFloat 1.8s ease-in-out infinite;
    border: 1px solid rgba(59, 130, 246, 0.35);
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}

.st-key-back_button button:hover {
    animation: backButtonWiggle 0.45s ease-in-out infinite;
    box-shadow: 0 14px 30px rgba(59, 130, 246, 0.55);
    filter: brightness(1.14) saturate(1.2);
}

/* Apply slideFadeDown animation to st.success (alert elements) */
div[data-testid="stAlert"] {
    animation: slideFadeDown 0.4s ease forwards;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

div[data-testid="stAlert"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12);
}
</style>
""")


if __name__ == '__main__':
    if not is_authenticated():
        login_screen(
            title='This app is private.',
            description='Log in with Google or create a secure local account to continue.',
        )
    else:
        local_user_name = st.session_state.get('local_user_name')
        google_name = getattr(st.user, 'name', '')
        display_name = local_user_name or google_name or 'there'
        st.header(f'Welcome, {display_name}!')
        st.caption(
            'Your account is ready. Use the sidebar to manage wardrobe, weather, and location.'
        )

        # ------ Creates 2 columns ----------
        leftcol, rightcol = st.columns([0.65, 0.35], gap='medium')

        with rightcol:
            with st.container(border=True):
                weather_slot = st.empty()
                with weather_slot.container():
                    render_panel_loading('Loading weather panel...', min_height_px=190)

            with st.container(border=True):
                stylist_slot = st.empty()
                with stylist_slot.container():
                    render_panel_loading('Loading AI Stylist...', min_height_px=170)

        with leftcol:
            with st.container(border=True):
                _display_wardrobe_preview()

        weather_location, weather_bundle, weather_error = _load_weather_panel_state()

        weather_slot.empty()
        with weather_slot.container():
            _display_weather(weather_location, weather_bundle, weather_error)

        stylist_slot.empty()
        with stylist_slot.container():
            _display_ai_stylist_panel()
