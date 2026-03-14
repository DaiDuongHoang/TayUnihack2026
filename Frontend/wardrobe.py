import streamlit as st
import time
from mainPage import add_clothe_item

danger_delete_button = None
LOG_DURATION_SECONDS = 3.8

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

div[data-testid="stColumn"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12);
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

@keyframes deleteLogFadeAway {
    0% {
        opacity: 0;
        transform: translateY(-6px);
        max-height: 48px;
    }
    12% {
        opacity: 1;
        transform: translateY(0);
        max-height: 48px;
    }
    78% {
        opacity: 1;
        transform: translateY(0);
        max-height: 48px;
    }
    100% {
        opacity: 0;
        transform: translateY(-4px);
        max-height: 0;
    }
}

.delete-log-wrap {
    position: static;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    pointer-events: none;
    width: fit-content;
    margin: 0 auto 0.72rem auto;
    padding: 0;
    line-height: 1;
}

.delete-log-pill {
    animation: deleteLogFadeAway 3.8s ease forwards;
    display: inline-block;
    font-size: 0.78rem;
    font-weight: 600;
    line-height: 1;
    padding: 0.38rem 0.62rem;
    border-radius: 999px;
    border: 1px solid rgba(239, 68, 68, 0.35);
    background: rgba(254, 242, 242, 0.95);
    color: #b91c1c;
    margin: 0 auto;
}

.delete-log-pill + .delete-log-pill {
    margin-top: -0.30rem;
}

@keyframes addLogFadeAway {
    0% {
        opacity: 0;
        transform: translateY(-6px);
        max-height: 48px;
    }
    12% {
        opacity: 1;
        transform: translateY(0);
        max-height: 48px;
    }
    78% {
        opacity: 1;
        transform: translateY(0);
        max-height: 48px;
    }
    100% {
        opacity: 0;
        transform: translateY(-4px);
        max-height: 0;
    }
}

.add-log-wrap {
    position: static;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    pointer-events: none;
    width: fit-content;
    margin: 0 auto 0.72rem auto;
    padding: 0;
    line-height: 1;
}

.add-log-pill {
    animation: addLogFadeAway 3.8s ease forwards;
    display: inline-block;
    font-size: 0.78rem;
    font-weight: 600;
    line-height: 1;
    padding: 0.38rem 0.62rem;
    border-radius: 999px;
    border: 1px solid rgba(16, 185, 129, 0.4);
    background: rgba(236, 253, 245, 0.98);
    color: #065f46;
    margin: 0 auto;
}

.add-log-pill + .add-log-pill {
    margin-top: -0.30rem;
}
</style>
""")

# Initialize session state
if "selected_category" not in st.session_state:
    st.session_state.selected_category = None


# !!! Clothes catalogue !!!
if "catalog" not in st.session_state:
    st.session_state.catalog = {
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

categories = list(st.session_state.catalog.keys())


# --- Top bar: Title + Action Buttons ---
st.title("👗 My Wardrobe")
st.divider()

if "wardrobe_delete_logs" not in st.session_state:
    st.session_state.wardrobe_delete_logs = []

if "wardrobe_add_logs" not in st.session_state:
    st.session_state.wardrobe_add_logs = []

feedback_message = st.session_state.pop("wardrobe_feedback", None)
if feedback_message:
    if feedback_message == "Item deleted.":
        st.session_state.wardrobe_delete_logs.append(
            {
                "id": time.time_ns(),
                "created_at": time.time(),
                "message": "Item deleted",
            }
        )
    elif feedback_message.startswith("Added "):
        st.session_state.wardrobe_add_logs.append(
            {
                "id": time.time_ns(),
                "created_at": time.time(),
                "message": feedback_message,
            }
        )
    else:
        st.success(feedback_message)

now = time.time()
st.session_state.wardrobe_delete_logs = [
    log
    for log in st.session_state.wardrobe_delete_logs
    if now - float(log.get("created_at", 0.0)) < LOG_DURATION_SECONDS
]

st.session_state.wardrobe_add_logs = [
    log
    for log in st.session_state.wardrobe_add_logs
    if now - float(log.get("created_at", 0.0)) < LOG_DURATION_SECONDS
]

if st.session_state.wardrobe_add_logs:
    add_logs_html = ["<div class='add-log-wrap'>"]
    for log in st.session_state.wardrobe_add_logs:
        age = max(0.0, now - float(log.get("created_at", now)))
        capped_age = min(LOG_DURATION_SECONDS, age)
        msg = str(log.get("message", "Added item"))
        add_logs_html.append(
            f"<div class='add-log-pill' style='animation-delay: -{capped_age:.3f}s'>{msg}</div>"
        )
    add_logs_html.append("</div>")
    st.markdown("".join(add_logs_html), unsafe_allow_html=True)

if st.session_state.wardrobe_delete_logs:
    delete_logs_html = ["<div class='delete-log-wrap'>"]
    for log in st.session_state.wardrobe_delete_logs:
        age = max(0.0, now - float(log.get("created_at", now)))
        capped_age = min(LOG_DURATION_SECONDS, age)
        msg = str(log.get("message", "Item deleted"))
        delete_logs_html.append(
            f"<div class='delete-log-pill' style='animation-delay: -{capped_age:.3f}s'>{msg}</div>"
        )
    delete_logs_html.append("</div>")
    st.markdown("".join(delete_logs_html), unsafe_allow_html=True)

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
                            st.session_state.wardrobe_delete_logs.append(
                                {
                                    "id": time.time_ns(),
                                    "created_at": time.time(),
                                    "message": "Item deleted",
                                }
                            )
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
