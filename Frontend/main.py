import streamlit as st
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGO_BIG = PROJECT_ROOT / "logo" / "Logobig2.png"
LOGO_ICON = PROJECT_ROOT / "logo" / "Logosmall2.png"

if LOGO_BIG.exists():
    if hasattr(st, "logo"):
        if LOGO_ICON.exists():
            st.logo(image=str(LOGO_BIG), size="large", icon_image=str(LOGO_ICON))
        else:
            st.logo(image=str(LOGO_BIG), size="large")
    else:
        st.sidebar.image(
            str(LOGO_BIG), use_container_width=True
        )  # RUN THIS IN STREAMLIT FIRST

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

st.set_page_config(
    page_title="Taylr",
    page_icon="👗",
    layout="centered",
    menu_items={
        "Get Help": "mailto:dhoa0014@student.monash.edu",
        "Report a bug": "mailto:mvan0078@student.monash.edu",
        "About": "Taylr is a personal wardrobe assistant that helps you manage your clothing items, plan outfits, and get weather-based recommendations. Built with Streamlit for a seamless and interactive experience.",
    },
)
pg = st.navigation(pages)
if __name__ == "__main__":
    pg.run()
