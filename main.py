import streamlit as st

pages = {
    "Home": [
        st.Page("wardrobe.py", title="Wardrobe", icon="👗"),
        st.Page("weather.py", title="Weather", icon="🌦️"),
        st.Page("location.py", title="Location", icon="🎈"),
    ]
}

pg = st.navigation(pages)
if __name__ == "__main__":
    pg.run()
