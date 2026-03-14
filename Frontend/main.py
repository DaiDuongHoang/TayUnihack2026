import streamlit as st

# RUN THIS IN STREAMLIT FIRST

pages = {
    "Home": [
        st.Page("mainPage.py", title="Home", icon="🏠"),
        st.Page("wardrobe.py", title="Wardrobe", icon="👗"),
        st.Page("weather.py", title="Weather", icon="🌦️"),
        st.Page("location.py", title="Location", icon="🎈"),
    ],
    #     "Settings": [
    #         st.Page("settings.py", title="Settings", icon="⚙️"),
    #     ],
}


pg = st.navigation(pages)
if __name__ == "__main__":
    pg.run()
