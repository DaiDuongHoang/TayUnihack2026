from turtle import right

import streamlit as st
from Authentication import is_authenticated, login_screen
import base64

# use wide layout so panels have more room
st.set_page_config(layout="wide")
from data_backend import add_clothing_item, get_user_location, get_user_catalog
from openweatherapi import fetch_weather_bundle
from weather import WeatherChartFactory

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

CLOTH_TYPE_OPTIONS = [
    "👕 T-Shirt",
    "🧥 Blazer",
    "👗 Dress",
    "🧥 Jacket",
    "🥼 Coat",
    "🧥 Hoodie",
    "🧶 Sweater",
    "🩲 Shorts",
    "👗 Skirt",
    "👖 Jeans",
    "👖 Pants",
    "🧢 Hat",
    "🕶️ Sunglasses",
    "🧣 Scarf",
    "🧤 Gloves",
]

CATEGORY_BY_CLOTH_TYPE = {
    "👕 T-Shirt": "Top 👚",
    "👗 Dress": "Top 👚",
    "🧶 Sweater": "Top 👚",
    "🩲 Shorts": "Bottom 🩳",
    "👗 Skirt": "Bottom 🩳",
    "👖 Jeans": "Bottom 🩳",
    "👖 Pants": "Bottom 🩳",
    "🧥 Blazer": "Outerwear 🧥",
    "🧥 Jacket": "Outerwear 🧥",
    "🥼 Coat": "Outerwear 🧥",
    "🧥 Hoodie": "Outerwear 🧥",
    "🧢 Hat": "Accessories ⌚",
    "🕶️ Sunglasses": "Accessories ⌚",
    "🧣 Scarf": "Accessories ⌚",
    "🧤 Gloves": "Accessories ⌚",
}


def _ensure_catalog_categories():
    if "catalog" not in st.session_state:
        st.session_state.catalog = {}

    for category in ("Top 👚", "Bottom 🩳", "Outerwear 🧥", "Accessories ⌚"):
        st.session_state.catalog.setdefault(category, [])


def _plain_cloth_type_name(cloth_type):
    return cloth_type.split(" ", 1)[1] if " " in cloth_type else cloth_type


def _add_item_to_catalog(name, cloth_type, image=None, color=None):
    _ensure_catalog_categories()
    category = CATEGORY_BY_CLOTH_TYPE.get(cloth_type, "Accessories ⌚")
    st.session_state.catalog[category].append(
        {
            "name": name,
            "image": image,
            "color": color,
            "cloth_type": cloth_type,
        }
    )
    return category


# Defining functions to display weather and wardrobe widgets

def _load_catalog_if_missing():
    if "catalog" not in st.session_state:
        local = st.session_state.get("local_user")
        if local:
            try:
                st.session_state.catalog = get_user_catalog(local)
            except Exception:
                st.session_state.catalog = {}
        else:
            st.session_state.catalog = {}


def _display_wardrobe_preview():
    _load_catalog_if_missing()
    catalog = st.session_state.get("catalog", {})
    items = []
    for cat, entries in catalog.items():
        for it in entries:
            if isinstance(it, dict):
                items.append({
                    "name": it.get("name", "Unnamed"),
                    "image": it.get("image"),
                    "color": it.get("color"),
                    "category": cat,
                })
            else:
                name, image = it
                items.append({"name": name, "image": image, "color": None, "category": cat})

    st.subheader("Wardrobe Preview")
    if not items:
        st.info("No wardrobe items available to preview.")
        return

    per_row = 3
    for i in range(0, len(items), per_row):
        cols = st.columns(per_row, gap="small")
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(items):
                break
            item = items[idx]
            with col:
                name = item.get("name")
                img = item.get("image")
                color = item.get("color")
                category = item.get("category")

                # prepare image or color block as HTML
                img_html = ""
                if img:
                    try:
                        if isinstance(img, (bytes, bytearray)):
                            b64 = base64.b64encode(img).decode("utf-8")
                            img_html = f'<img src="data:image/png;base64,{b64}" style="width:100%;height:140px;object-fit:cover;border-radius:8px;"/>'
                        else:
                            img_html = f'<img src="{img}" style="width:100%;height:140px;object-fit:cover;border-radius:8px;"/>'
                    except Exception:
                        img_html = '<div style="width:100%;height:140px;display:flex;align-items:center;justify-content:center;background:#f3f4f6;border-radius:8px;">(image)</div>'
                elif color:
                    img_html = f'<div style="width:100%;height:140px;border-radius:8px;background:{color};border:1px solid rgba(0,0,0,0.06);"></div>'

                card_html = f'''<div style="border-radius:12px;padding:10px;border:1px solid rgba(0,0,0,0.06);box-shadow:0 6px 18px rgba(0,0,0,0.06);">\
                    <div style=\"font-weight:600;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;\">{name}</div>\
                    {img_html}\
                    <div style=\"margin-top:8px;color:#6b7280;font-size:0.9rem;\">{category}</div>\
                </div>'''

                st.markdown(card_html, unsafe_allow_html=True)


def _display_weather():
    local = st.session_state.get("local_user")

    # --- Weather ---
    location = None
    if local:
        try:
            loc = get_user_location(local)
            location = (loc.get("city", ""), loc.get("country", ""))
        except Exception:
            location = None

    if not location:
        # let user enter a location if not found
        city = st.text_input("Enter city for weather", value="")
        country = st.text_input("Country (optional)", value="")
        if city:
            location = (city, country)

    if location:
        try:
            bundle = fetch_weather_bundle(location[0], location[1])
            cur = bundle.get("current", {})
            main = cur.get("main", {})
            weather = cur.get("weather", [{}])[0]

            # compute emoji for header from weather description
            try:
                desc_text = (weather.get('main') or weather.get('description') or '').strip()
                emoji = WeatherChartFactory._description_emoji(desc_text)
            except Exception:
                emoji = ''

            st.subheader(f"Weather Panel {emoji}")


            cols = st.columns([1, 2])
            with cols[0]:
                temp_val = main.get("temp", None)
                try:
                    temp_text = f"{float(temp_val):.1f}"
                except Exception:
                    temp_text = "N/A"
                st.metric("Temp (°C)", temp_text)
                st.caption(bundle.get("location", ""))
            with cols[1]:
                st.markdown(f"**{weather.get('main', '')}** — {weather.get('description', '')}")
                st.write(f"**Humidity**: {main.get('humidity', 'N/A')}%")
                st.write(f"**Wind**: {cur.get('wind', {}).get('speed', 'N/A')} m/s")
        except Exception as e:
            st.warning(f"Unable to fetch weather: {e}")
    else:
        st.info("No location provided for weather.")


@st.dialog("Add a new clothe item")
def add_clothe_item():
    item_name = st.text_input(
        "**Clothe Item Name**",
        placeholder="Enter the item name",
        help="Example: White Office Shirt, Black Wide-Leg Pants",
    )

    uploaded_files = st.file_uploader(
        "Upload image(s) of the clothe item",
        type=["jpg", "jpeg", "png", "bmp"],
        help="Supported formats: JPG, JPEG, PNG, BMP. Max file size: 10MB.",
        accept_multiple_files=True,
    )

    has_uploaded_files = bool(uploaded_files)
    selected_cloth_type = None
    manual_color = None

    if has_uploaded_files:
        for file in uploaded_files:
            st.image(file, caption=file.name)
        st.success(f"Successfully uploaded {len(uploaded_files)} file(s)!")
    else:
        st.info("Upload an image, or enter the clothe details manually to continue.")

        selected_cloth_type = st.selectbox(
            "**Clothe Type**",
            CLOTH_TYPE_OPTIONS,
            index=None,
            placeholder="Select a clothe type",
            help="The wardrobe category will be assigned automatically from this type.",
        )

        manual_color = st.color_picker(
            "**Color**", help="Choose the color of the clothe item", width="stretch"
        )

    clean_item_name = item_name.strip()
    manual_entry_ready = (
        selected_cloth_type is not None
        and manual_color is not None
        and bool(clean_item_name)
    )
    upload_entry_ready = has_uploaded_files and bool(clean_item_name)

    if upload_entry_ready or manual_entry_ready:
        if st.button("Submit", type="primary", use_container_width=True):
            local_email = st.session_state.get("local_user")

            if has_uploaded_files:
                category = None
                for index, file in enumerate(uploaded_files, start=1):
                    uploaded_item_name = clean_item_name
                    if len(uploaded_files) > 1:
                        uploaded_item_name = f"{clean_item_name} {index}"

                    image_data = file.getvalue()

                    category = _add_item_to_catalog(
                        name=uploaded_item_name,
                        cloth_type=None,
                        image=image_data,
                    )
                    if local_email:
                        add_clothing_item(
                            email=local_email,
                            item_name=uploaded_item_name,
                            image_data=image_data,
                        )
                st.session_state.wardrobe_feedback = (
                    f"**Added {len(uploaded_files)} item(s) to {category}.**"
                )
            else:
                category = _add_item_to_catalog(
                    name=clean_item_name,
                    cloth_type=selected_cloth_type,
                    color=manual_color,
                )
                if local_email:
                    add_clothing_item(
                        email=local_email,
                        item_name=clean_item_name,
                        cloth_type=selected_cloth_type,
                        color=manual_color,
                        wardrobe_category=category,
                    )
                st.session_state.wardrobe_feedback = f"**Added {_plain_cloth_type_name(selected_cloth_type)} to {category}.**"

            st.rerun()


if __name__ == "__main__":
    if not is_authenticated():
        login_screen(
            title="This app is private.",
            description="Log in with Google or create a secure local account to continue.",
        )
    else:
        local_user_name = st.session_state.get("local_user_name")
        google_name = getattr(st.user, "name", "")
        display_name = local_user_name or google_name or "there"
        st.header(f"Welcome, {display_name}!")
        st.caption(
            "Your account is ready. Use the sidebar to manage wardrobe, weather, and location."
        )
        
        # ------ Creates 2 columns ----------
        leftcol, rightcol = st.columns([0.65, 0.35], gap="medium")

        with leftcol:
            with st.container(border=True):
            
                _display_wardrobe_preview()


        with rightcol:
            with st.container(border=True):
                _display_weather()
