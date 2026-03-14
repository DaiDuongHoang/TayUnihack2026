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
