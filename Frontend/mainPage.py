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
                    f"Added {len(uploaded_files)} item(s) to {category}."
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
                st.session_state.wardrobe_feedback = f"Added {_plain_cloth_type_name(selected_cloth_type)} to {category}."

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
