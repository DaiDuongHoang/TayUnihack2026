import streamlit as st

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

# --- Add Clothes Dialog ---
@st.dialog("Add Clothing Item")
def add_clothing():
    category = st.selectbox("Select Category", categories)
    name = st.text_input("Item Name")
    image_url = st.text_input("Image URL")
    if st.button("Add", use_container_width=True):
        if name and image_url:
            st.session_state.catalog[category].append((name, image_url))
            st.rerun()
        else:
            st.warning("Please fill in both name and image URL.")

# --- Delete Clothes Dialog ---
@st.dialog("Delete Clothing Item")
def delete_clothing():
    category = st.selectbox("Select Category", categories)
    items = st.session_state.catalog[category]
    if items:
        item_names = [item[0] for item in items]
        to_delete = st.selectbox("Select Item to Delete", item_names)
        if st.button("Delete", use_container_width=True):
            st.session_state.catalog[category] = [
                item for item in items if item[0] != to_delete
            ]
            st.rerun()
    else:
        st.info("No items in this category.")

# --- Top bar: Title + Action Buttons ---
title_col, spacer, add_col, del_col = st.columns([6, 1, 0.5, 0.5])
with title_col:
    st.title("My Wardrobe")
with add_col:
    if st.button("➕", use_container_width=True):
        add_clothing()
with del_col:
    if st.button("🗑️", use_container_width=True):
        delete_clothing()

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
            if st.button(f"Open {category}", key=f"cat_{category}", use_container_width=True):
                st.session_state.selected_category = category
                st.rerun()

# --- Clothing Grid ---
else:
    if st.button("← Back to Categories"):
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
                        st.markdown(f"#### {name}")  # Adjust # level for size, add more # to decrease font size
                        st.image(image)