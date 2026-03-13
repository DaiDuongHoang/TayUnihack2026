"""
app.py – AI Outfit Planner · Main Streamlit entry point.

Run with:
    streamlit run app.py
"""

import streamlit as st

from modules.database import init_db, add_item, get_all_items
from modules.cv_handler import load_image, detect_clothing, classify_item
from modules.weather_api import get_melbourne_weather, weather_to_tags
from modules.engine import recommend_outfit, build_complete_outfit

# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Outfit Planner",
    page_icon="👗",
    layout="wide",
)

# Initialise the SQLite database (creates wardrobe.db if it doesn't exist).
init_db()

# ---------------------------------------------------------------------------
# Sidebar – Weather Forecast
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🌤 Melbourne Weather")
    st.divider()

    weather = get_melbourne_weather()
    icon_url = (
        f"https://openweathermap.org/img/wn/{weather['icon']}@2x.png"
        if weather.get("icon")
        else None
    )
    if icon_url:
        st.image(icon_url, width=80)

    st.metric("Temperature", f"{weather['temperature']:.1f} °C")
    st.metric("Humidity", f"{weather['humidity']} %")
    st.metric("Wind Speed", f"{weather['wind_speed']:.1f} m/s")
    st.write(f"**Condition:** {weather['description']}")

    st.divider()
    weather_tags = weather_to_tags(weather)
    st.write("**Outfit tags:**", ", ".join(weather_tags) if weather_tags else "—")

    if st.button("🔄 Refresh Weather"):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("👗 AI Outfit Planner")
st.caption("Upload clothes to your virtual wardrobe, then get AI-powered outfit suggestions based on Melbourne's weather.")

tab_upload, tab_wardrobe, tab_suggest = st.tabs(
    ["📤 Upload Image", "🗄 My Wardrobe", "✨ Get Suggestion"]
)

# -----------------------------------------------------------
# Tab 1 – Upload Image
# -----------------------------------------------------------
with tab_upload:
    st.header("Add a Clothing Item")
    st.write("Upload a photo of a garment and we will detect and classify it for you.")

    uploaded_file = st.file_uploader(
        "Choose an image…",
        type=["jpg", "jpeg", "png", "webp"],
        help="Supported formats: JPG, PNG, WEBP",
    )

    if uploaded_file is not None:
        col_img, col_form = st.columns([1, 1])

        with col_img:
            st.image(uploaded_file, caption="Uploaded image", use_container_width=True)

        with col_form:
            st.subheader("Detected clothing")

            # Run CV detection (uses placeholder logic until YOLO is wired up).
            image_array = load_image(uploaded_file)
            detections = detect_clothing(image_array)

            if detections:
                for det in detections:
                    category = classify_item(det["label"])
                    st.write(
                        f"- **{det['label'].title()}** "
                        f"(category: `{category}`, "
                        f"confidence: {det['confidence']:.0%})"
                    )
            else:
                st.info("No clothing items detected.")

            st.subheader("Save to wardrobe")
            with st.form("add_item_form"):
                item_name = st.text_input(
                    "Item name",
                    value=detections[0]["label"].title() if detections else "",
                )
                item_category = st.selectbox(
                    "Category",
                    ["top", "bottom", "outerwear", "shoes", "accessory", "other"],
                    index=0,
                )
                item_tags = st.text_input(
                    "Tags (comma-separated)",
                    placeholder="e.g. casual, warm, blue",
                )
                submitted = st.form_submit_button("💾 Add to wardrobe")

            if submitted:
                if item_name.strip():
                    new_id = add_item(
                        name=item_name.strip(),
                        category=item_category,
                        # TODO (team): persist the uploaded image to disk and store its path.
                        image_path="",
                        tags=item_tags.strip(),
                    )
                    st.success(f"Added **{item_name}** (id: {new_id}) to your wardrobe!")
                else:
                    st.warning("Please enter an item name before saving.")

# -----------------------------------------------------------
# Tab 2 – My Wardrobe
# -----------------------------------------------------------
with tab_wardrobe:
    st.header("My Wardrobe")

    items = get_all_items()
    if not items:
        st.info("Your wardrobe is empty. Upload some clothes to get started!")
    else:
        st.write(f"**{len(items)} item(s)** in your wardrobe.")
        st.dataframe(
            items,
            column_order=["id", "name", "category", "tags", "added_at"],
            use_container_width=True,
        )

# -----------------------------------------------------------
# Tab 3 – Get Suggestion
# -----------------------------------------------------------
with tab_suggest:
    st.header("Today's Outfit Suggestion")
    st.write(
        f"Based on the current Melbourne weather "
        f"(**{weather['description']}**, {weather['temperature']:.1f} °C), "
        f"here are the best picks from your wardrobe:"
    )

    items = get_all_items()
    if not items:
        st.info("Add some clothes to your wardrobe first!")
    else:
        outfit = build_complete_outfit(items, weather_tags)
        ranked = recommend_outfit(items, weather_tags)

        st.subheader("🎽 Complete Outfit")
        has_suggestion = any(v is not None for v in outfit.values())
        if has_suggestion:
            cols = st.columns(len(outfit))
            for col, (category, item) in zip(cols, outfit.items()):
                with col:
                    st.markdown(f"**{category.title()}**")
                    if item:
                        st.write(item["name"])
                        st.caption(f"Tags: {item['tags'] or '—'}")
                    else:
                        st.write("—")
        else:
            st.warning("No matching items found for today's weather.")

        st.subheader("📋 All Ranked Items")
        st.dataframe(
            ranked,
            column_order=["name", "category", "tags", "score"],
            use_container_width=True,
        )
