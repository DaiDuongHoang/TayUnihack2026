import streamlit as st
from mainPage import add_clothe_item

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
    transform: scale(1.03);
    box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.2);
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

# --- Category Grid (2x2) ---
if st.session_state.selected_category is None:
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
                    name, image = items[i + j]
                    with col:
                        st.markdown(
                            f"#### {name}"
                        )  # Adjust # level for size, add more # to decrease font size
                        st.image(image)
