import streamlit as st
import importlib

# Optional backend integration.
# Update BACKEND_MODULE if your backend file uses a different module name.
BACKEND_MODULE = "auth_backend"


def load_backend_functions():
    try:
        module = importlib.import_module(BACKEND_MODULE)
    except ModuleNotFoundError:
        return None, None

    register_fn = getattr(module, "register_user", None)
    verify_fn = getattr(module, "verify_user", None)
    return register_fn, verify_fn


backend_register_user, backend_verify_user = load_backend_functions()


def register_user(username: str, password: str) -> tuple[bool, str]:
    if backend_register_user is None:
        return (
            False,
            "Backend register function is not connected. "
            "Expose auth_backend.register_user(username, password) and re-run.",
        )
    return backend_register_user(username.strip(), password)


def authenticate_local_user(username: str, password: str) -> tuple[bool, str]:
    if backend_verify_user is None:
        return (
            False,
            "Backend verify function is not connected. "
            "Expose auth_backend.verify_user(username, password) and re-run.",
        )

    is_valid = backend_verify_user(username.strip(), password)
    if is_valid:
        return True, "Login successful."
    return False, "Invalid username or password."


def login_screen() -> None:
    st.header("This app is private")
    st.write("Sign in with Google or use a local account.")

    login_tab, register_tab = st.tabs(["Log in", "Register"])

    with login_tab:
        st.subheader("Google login")
        st.button("Log in with Google", on_click=st.login, use_container_width=True)
        st.caption(
            "Google login requires Streamlit auth settings in .streamlit/secrets.toml."
        )

        st.divider()
        st.subheader("Local login")
        with st.form("local_login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", use_container_width=True)

        if submitted:
            is_valid, message = authenticate_local_user(username, password)
            if is_valid:
                st.session_state.local_user = username.strip()
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    with register_tab:
        st.subheader("Create local account")
        with st.form("local_register_form"):
            username = st.text_input(
                "New username", placeholder="Choose a unique username"
            )
            password = st.text_input("New password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button(
                "Create account", use_container_width=True
            )

        if submitted:
            if password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, message = register_user(username, password)
                if success:
                    st.success(message)
                else:
                    st.error(message)


def authenticated_view() -> None:
    google_logged_in = bool(st.user.is_logged_in)
    local_user = st.session_state.get("local_user")

    if google_logged_in:
        display_name = st.user.name or "Google user"
        st.header(f"Welcome, {display_name}!")
        st.caption("Authenticated with Google")
    elif local_user:
        st.header(f"Welcome, {local_user}!")
        st.caption("Authenticated with local username/password")

    col1, col2 = st.columns(2)
    with col1:
        if google_logged_in:
            st.button("Log out (Google)", on_click=st.logout, use_container_width=True)
    with col2:
        if local_user:
            if st.button("Log out (Local)", use_container_width=True):
                st.session_state.local_user = None
                st.rerun()


def main() -> None:
    st.set_page_config(page_title="Authentication", page_icon="🔐")

    if "local_user" not in st.session_state:
        st.session_state.local_user = None

    if st.user.is_logged_in or st.session_state.local_user:
        authenticated_view()
    else:
        login_screen()


if __name__ == "__main__":
    main()
