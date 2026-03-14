import streamlit as st
import importlib
import base64
from pathlib import Path

# Optional backend integration.
# Update BACKEND_MODULE if your backend file uses a different module name.
BACKEND_MODULE = "auth_backend"


def load_backend_functions():
    try:
        module = importlib.import_module(BACKEND_MODULE)
    except ModuleNotFoundError:
        return None, None, None, None

    register_fn = getattr(module, "register_user", None)
    verify_fn = getattr(module, "verify_user", None)
    authenticate_fn = getattr(module, "authenticate_user", None)
    google_sync_fn = getattr(module, "sync_google_user", None)
    return register_fn, verify_fn, authenticate_fn, google_sync_fn


(
    backend_register_user,
    backend_verify_user,
    backend_authenticate_user,
    backend_sync_google_user,
) = load_backend_functions()


def register_user(first_name: str, email: str, password: str) -> tuple[bool, str]:
    if backend_register_user is None:
        return (
            False,
            "Backend register function is not connected. "
            "Expose auth_backend.register_user(first_name, email, password) and re-run.",
        )
    return backend_register_user(first_name.strip(), email.strip(), password)


def authenticate_local_user(email: str, password: str) -> tuple[bool, str, dict | None]:
    if backend_authenticate_user is not None:
        return backend_authenticate_user(email.strip(), password)

    if backend_verify_user is None:
        return (
            False,
            "Backend verify function is not connected. "
            "Expose auth_backend.verify_user(email, password) and re-run.",
            None,
        )

    is_valid = backend_verify_user(email.strip(), password)
    if is_valid:
        return (
            True,
            "Login successful.",
            {"email": email.strip().lower(), "first_name": "User"},
        )
    return False, "Invalid email or password.", None


def is_google_logged_in() -> bool:
    return bool(getattr(st.user, "is_logged_in", False))


def is_authenticated() -> bool:
    return is_google_logged_in() or bool(st.session_state.get("local_user"))


def _sync_google_profile() -> dict | None:
    if not is_google_logged_in():
        return None

    email = getattr(st.user, "email", "") or ""
    full_name = getattr(st.user, "name", "") or "Google user"
    first_name = full_name.split(" ", 1)[0]
    google_subject = getattr(st.user, "sub", None)

    if backend_sync_google_user is None or not email:
        return {"email": email, "first_name": first_name}

    return backend_sync_google_user(email, first_name, google_subject)


def _set_local_session(profile: dict) -> None:
    st.session_state.local_user = profile.get("email")
    st.session_state.local_user_name = profile.get("first_name") or "User"


def _inject_auth_styles() -> None:
    icon_path = Path(__file__).resolve().parent.parent / "logo" / "icon.png"
    if not icon_path.exists():
        return

    icon_base64 = base64.b64encode(icon_path.read_bytes()).decode("utf-8")
    st.markdown(
        f"""
        <style>
        .st-key-google_login_button button,
        .st-key-google_register_button button {{
            background-color: #ffffff !important;
            color: #1f1f1f !important;
            border: 1px solid #dadce0 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            background-image: url("data:image/png;base64,{icon_base64}") !important;
            background-repeat: no-repeat !important;
            background-position: 14px center !important;
            background-size: 20px 20px !important;
            padding-left: 44px !important;
        }}

        .st-key-google_login_button button:hover,
        .st-key-google_register_button button:hover {{
            border-color: #c6c9cc !important;
            box-shadow: 0 1px 2px rgba(60, 64, 67, 0.2) !important;
        }}

        .st-key-local_register_submit button {{
            border-radius: 8px !important;
            font-weight: 600 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def login_screen(
    title: str = "This app is private",
    description: str = "Sign in with Google or use a local account.",
) -> None:
    _inject_auth_styles()
    st.header(title)
    st.write(description)

    login_tab, register_tab = st.tabs(["Log in", "Register"])

    with login_tab:
        st.subheader("Local login")
        with st.form("local_login_form"):
            email = st.text_input("Email", placeholder="Enter your email address")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(
                "Log in",
                use_container_width=True,
                type="primary",
                key="local_login_submit",
            )

        if submitted:
            is_valid, message, profile = authenticate_local_user(email, password)
            if is_valid:
                _set_local_session(
                    profile or {"email": email.strip().lower(), "first_name": "User"}
                )
                st.success(message)
                st.rerun()
            else:
                st.error(message)

        st.caption("Or continue with Google")
        st.button(
            "Log in with Google",
            on_click=st.login,
            use_container_width=True,
            key="google_login_button",
        )
        st.caption(
            "Google login requires Streamlit auth settings in .streamlit/secrets.toml."
        )

    with register_tab:
        st.subheader("Create local account")
        st.info(
            "Password rule: at least 8 characters, with 1 uppercase letter, 1 lowercase letter, and 1 number."
        )
        with st.form("local_register_form"):
            first_name = st.text_input(
                "First name", placeholder="Enter your first name"
            )
            email = st.text_input("Email", placeholder="Enter your email address")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button(
                "Create account",
                use_container_width=True,
                type="primary",
                key="local_register_submit",
            )

        st.caption("Local passwords are stored using salted PBKDF2-SHA256 hashing.")

        if submitted:
            if password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, message = register_user(first_name, email, password)
                if success:
                    _set_local_session(
                        {
                            "email": email.strip().lower(),
                            "first_name": first_name.strip() or "User",
                        }
                    )
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        st.button(
            "Sign up with Google",
            on_click=st.login,
            use_container_width=True,
            key="google_register_button",
        )
        st.caption(
            "Google registration requires Streamlit auth settings in .streamlit/secrets.toml."
        )


def authenticated_view() -> None:
    google_logged_in = is_google_logged_in()
    local_user = st.session_state.get("local_user")
    local_user_name = st.session_state.get("local_user_name")

    if google_logged_in:
        google_profile = _sync_google_profile()
        display_name = (
            getattr(st.user, "name", "")
            or (google_profile or {}).get("first_name")
            or "Google user"
        )
        st.header(f"Welcome, {display_name}!")
        google_email = getattr(st.user, "email", "") or (google_profile or {}).get(
            "email", ""
        )
        if google_email:
            st.caption(f"Authenticated with Google: {google_email}")
        else:
            st.caption("Authenticated with Google")
    elif local_user:
        st.header(f"Welcome, {local_user_name or local_user}!")
        st.caption(f"Authenticated with local email/password: {local_user}")

    col1, col2 = st.columns(2)
    with col1:
        if google_logged_in:
            st.button("Log out (Google)", on_click=st.logout, use_container_width=True)
    with col2:
        if local_user:
            if st.button("Log out (Local)", use_container_width=True):
                st.session_state.local_user = None
                st.session_state.local_user_name = None
                st.rerun()


def main() -> None:
    st.set_page_config(page_title="Authentication", page_icon="🔐")

    if "local_user" not in st.session_state:
        st.session_state.local_user = None
    if "local_user_name" not in st.session_state:
        st.session_state.local_user_name = None

    if is_authenticated():
        authenticated_view()
    else:
        login_screen()


if __name__ == "__main__":
    main()
