import streamlit as st


@st.dialog("Add a new clothe item")
def add_clothe_item():
    uploaded_files = st.file_uploader(
        "Upload image(s) of the clothe item",
        type=["jpg", "jpeg", "png", "bmp"],
        help="Supported formats: JPG, JPEG, PNG, BMP. Max file size: 10MB.",
        accept_multiple_files=True,
    )

    has_uploaded_files = bool(uploaded_files)
    manual_cloth_type = None
    manual_color = None

    if has_uploaded_files:
        for file in uploaded_files:
            st.image(file, caption=file.name)
        st.success(f"Successfully uploaded {len(uploaded_files)} file(s)!")
    else:
        st.info("Upload an image, or enter the clothe details manually to continue.")

        manual_cloth_type = st.selectbox(
            "**Clothe Type**",
            [
                "T-Shirt",
                "Blazer",
                "Dress",
                "Jacket",
                "Coat",
                "Hoodie",
                "Sweater",
                "Shorts",
                "Skirt",
                "Jeans",
                "Pants",
            ],
            index=None,
            placeholder="Select a clothe type",
            help="Select the type of clothe item",
        )

        manual_color = st.color_picker(
            "**Color**", help="Choose the color of the clothe item", width="stretch"
        )

    manual_entry_ready = manual_cloth_type is not None and manual_color is not None

    if has_uploaded_files or manual_entry_ready:
        if st.button("Submit", type="primary", use_container_width=True):
            if has_uploaded_files:
                st.success("Clothe item submitted successfully.")
            else:
                st.success(
                    f"Manual entry submitted for a {manual_cloth_type} item in {manual_color}."
                )


if __name__ == "__main__":
    if st.button("Add Clothe Item", type="primary"):
        add_clothe_item()
