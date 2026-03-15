import streamlit as st
from Authentication import is_authenticated, login_screen
from data_backend import get_user_catalog
from dashboard import add_clothe_item

danger_delete_button = None

if not is_authenticated():
    login_screen(
        title="Sign in to access your wardrobe",
        description="Use Google or your local email/password account to continue.",
    )
    st.stop()

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
    animation: slideFadeDown 0.65s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

/* Apply to bordered column/grid boxes */
div[data-testid="stColumn"] {
    animation: slideFadeDown 0.65s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    transition: transform 0.28s ease, box-shadow 0.28s ease;
}

div[data-testid="stColumn"]:hover {
    transform: translateY(-10px) scale(1.01);
    box-shadow: 0 22px 48px rgba(0, 0, 0, 0.20);
}

/* Apply to horizontal divider */
div[data-testid="stDivider"] {
    animation: slideFadeDown 0.65s cubic-bezier(0.34, 1.56, 0.64, 1) 0.3s both;
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
    transform: translateY(-5px) scale(1.11);
    box-shadow: 0px 18px 36px rgba(0, 0, 0, 0.36);
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
/* Delete button — danger pulse idle + shake on hover */
@keyframes deleteDangerPulse {
    0%, 100% {
        box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.0);
        border-color: rgba(239, 68, 68, 0.28);
    }
    50% {
        box-shadow: 0 0 0 7px rgba(239, 68, 68, 0.18);
        border-color: rgba(239, 68, 68, 0.65);
    }
}

@keyframes deleteShake {
    0%   { transform: translateX(0) scale(1.04); }
    25%  { transform: translateX(-2px) scale(1.05); }
    50%  { transform: translateX(2px) scale(1.06); }
    75%  { transform: translateX(-1px) scale(1.05); }
    100% { transform: translateX(0) scale(1.04); }
}

[class*="st-key-del"] button {
    animation: slideFadeDown 0.65s cubic-bezier(0.34, 1.56, 0.64, 1) both,
               deleteDangerPulse 2.0s ease-in-out 0.7s infinite !important;
    border: 1.5px solid rgba(239, 68, 68, 0.32) !important;
    color: #dc2626 !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease,
                background 0.18s ease, border-color 0.18s ease !important;
}

[class*="st-key-del"] button:hover {
    animation: deleteShake 0.42s ease-in-out infinite !important;
    box-shadow: 0 14px 34px rgba(239, 68, 68, 0.55) !important;
    background: rgba(254, 226, 226, 0.88) !important;
    border-color: rgba(239, 68, 68, 0.75) !important;
    color: #b91c1c !important;
}

/* Apply slideFadeDown animation to st.success (alert elements) */
div[data-testid="stAlert"] {
    animation: slideFadeDown 0.65s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

div[data-testid="stAlert"]:hover {
    transform: translateY(-6px);
    box-shadow: 0 14px 32px rgba(0, 0, 0, 0.14);
}

</style>
""")

# Initialize session state
if "selected_category" not in st.session_state:
    st.session_state.selected_category = None


def _default_catalog():
    return {
        "Top 👚": [
            ("White T-Shirt", "https://static.streamlit.io/examples/cat.jpg"),
            ("Blue Polo", "https://static.streamlit.io/examples/dog.jpg"),
            ("Striped Shirt", "https://static.streamlit.io/examples/owl.jpg"),
        ],
        "Bottom 🩳": [
            ("Black Jeans", "https://static.streamlit.io/examples/cat.jpg"),
            ("Chinos", "https://static.streamlit.io/examples/dog.jpg"),
            ("Joggers", "https://static.streamlit.io/examples/owl.jpg"),
        ],
        "Outerwear 🧥": [
            ("Denim Jacket", "https://static.streamlit.io/examples/cat.jpg"),
            ("Trench Coat", "https://static.streamlit.io/examples/dog.jpg"),
            ("Puffer Vest", "https://static.streamlit.io/examples/owl.jpg"),
        ],
        "Accessories ⌚": [
            ("Leather Belt", "https://static.streamlit.io/examples/cat.jpg"),
            ("Wool Scarf", "https://static.streamlit.io/examples/dog.jpg"),
            ("Baseball Cap", "https://static.streamlit.io/examples/owl.jpg"),
        ],
    }


# !!! Clothes catalogue !!!
local_user = st.session_state.get("local_user")
if "catalog_owner" not in st.session_state:
    st.session_state.catalog_owner = None

if "catalog" not in st.session_state or st.session_state.catalog_owner != local_user:
    if local_user:
        st.session_state.catalog = get_user_catalog(local_user)
    else:
        st.session_state.catalog = _default_catalog()
    st.session_state.catalog_owner = local_user

categories = list(st.session_state.catalog.keys())


# --- Top bar: Title + Action Buttons ---
st.title("👗 My Wardrobe")
st.divider()

feedback_message = st.session_state.pop("wardrobe_feedback", None)
if feedback_message:
    if feedback_message == "Item deleted.":
        st.toast("**Item deleted**", icon="❌", duration="short")
    elif "Added " in feedback_message:
        st.toast(feedback_message, icon="✅", duration="short")
    else:
        st.success(feedback_message)

# --- Category Grid (2x2) ---
if st.session_state.selected_category is None:
    if st.button(
        "Add Item",
        key="add_item_button",
        type="primary",
        use_container_width=True,
        icon="➕",
    ):
        add_clothe_item()

    row1 = st.columns(2, border=True)
    row2 = st.columns(2, border=True)
    grid = [row1[0], row1[1], row2[0], row2[1]]

    for i, category in enumerate(categories):
        with grid[i]:
            st.markdown(f"### {category}")
            st.write(f"{len(st.session_state.catalog[category])} item(s)")
            if st.button(
                f"Open {category}", key=f"cat_{category}", use_container_width=True
            ):
                st.session_state.selected_category = category
                st.rerun()

# --- Clothing Grid ---
else:
    if st.button(
        "**Go Back**",
        key="back_button",
        type="primary",
        icon="⬅️",
    ):
        st.session_state.selected_category = None
        st.rerun()

    st.subheader(st.session_state.selected_category)
    items = st.session_state.catalog[st.session_state.selected_category]

    if not items:
        st.info("No items in this category yet. Use ➕ to add some!")
    else:
        num_cols = 3
        for i in range(0, len(items), num_cols):
            cols = st.columns(num_cols, border=True)
            for j, col in enumerate(cols):
                if i + j < len(items):
                    item = items[i + j]
                    if isinstance(item, dict):
                        name = item.get("name", "Unnamed Item")
                        image = item.get("image")
                        color = item.get("color")
                        cloth_type = item.get("cloth_type")
                    else:
                        name, image = item
                        color = None
                        cloth_type = None

                    with col:
                        st.markdown(f"#### {name}")

                        if cloth_type:
                            st.caption(cloth_type)

                        if image:
                            st.image(image, width="content")
                        elif color:
                            st.markdown(
                                f"<div style='width: 100%; height: 180px; border-radius: 0.75rem; background: {color}; border: 1px solid rgba(0, 0, 0, 0.08);'></div>",
                                unsafe_allow_html=True,
                            )
                            st.caption(f"Color: {color}")

                        item_index = i + j

                        def _delete_item(idx=item_index):
                            st.session_state.catalog[
                                st.session_state.selected_category
                            ].pop(idx)
                            st.session_state.wardrobe_feedback = "Item deleted."
                            st.rerun()

                        delete_key = (
                            f"del_{st.session_state.selected_category}_{item_index}"
                        )
                        if danger_delete_button is not None:
                            danger_delete_button(
                                key=delete_key,
                                data={
                                    "start": "Hold to Delete",
                                    "continue": "Keep holding...",
                                    "completed": "Deleted",
                                },
                                on_confirmed_change=_delete_item,
                                width="content",
                            )
                        else:
                            if st.button(
                                "Delete",
                                key=f"{delete_key}_fallback",
                                type="secondary",
                                icon="🗑️",
                                use_container_width=True,
                            ):
                                _delete_item()
