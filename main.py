import streamlit as st

st.set_page_config(page_title="UniHack 2026 - Outfit Planner", layout="wide")

st.title("👗 AI Outfit Planner - Team TayUnihack")

# Add sidebar navigation
locationPage = st.Page("location.py", title="Location", icon="🎈")
mainDashboardPage = st.Page("main_dashboard.py", title="Dashboard", icon="🎯")
statsPage = st.Page("stats.py", title="Statistics", icon="📊")
wardrobePage = st.Page("wardrobe.py", title="Wardrobe", icon="👕")
weatherPage = st.Page("weather.py", title="Weather", icon="🌦️")

pg = st.navigation([locationPage, mainDashboardPage, statsPage, wardrobePage])
pg.run()

col1, col2 = st.columns(2)

with col1:
    st.header("Tải ảnh quần áo")
    uploaded_file = st.file_uploader("Chọn một tấm ảnh...", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="Ảnh đã tải lên", use_column_width=True)

with col2:
    st.header("Gợi ý phối đồ")
    st.info("Hệ thống đang chờ ảnh và dữ liệu thời tiết...")

    # Nút bấm test thử
    if st.button("Dự đoán thử"):
        st.success(
            "Hôm nay trời Melbourne 15 độ, Duy nên mặc Hoodie này với quần Jean!"
        )
