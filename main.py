import streamlit as st

pages = {
    "Home": [
        st.Page("Wardrobe", "wardrobe.py"),
        st.Page("Weather", "weather.py"),
        st.Page("Location", "location.py"),
    ]
}

pg = st.navigation_bar(pages, "Home")
pg.run()
