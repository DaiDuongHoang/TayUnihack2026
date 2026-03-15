import streamlit as st
from Authentication import is_authenticated, login_screen


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
