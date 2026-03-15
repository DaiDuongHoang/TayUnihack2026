from turtle import right

import streamlit as st
from Authentication import is_authenticated, login_screen
from data_backend import add_clothing_item


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
