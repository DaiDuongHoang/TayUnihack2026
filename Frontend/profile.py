import streamlit as st
from Authentication import is_authenticated, login_screen, is_google_logged_in, is_guest
import auth_backend


def _inject_profile_styles() -> None:
    st.markdown(
        """
        <style>
        @keyframes profileFadeUp {
            from {
                opacity: 0;
                transform: translateY(16px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes profileAvatarFloat {
            0%,
            100% {
                transform: translateY(0);
            }
            50% {
                transform: translateY(-5px);
            }
        }

        .profile-hero {
            animation: profileFadeUp 0.55s ease-out both;
        }

        .profile-card {
            display: flex;
            align-items: center;
            gap: 1.2rem;
            padding: 1.2rem 1.4rem;
            border-radius: 18px;
            border: 1px solid rgba(148, 163, 184, 0.2);
            background: linear-gradient(135deg, rgba(255,255,255,0.97), rgba(239,246,255,0.94));
            box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
            margin-bottom: 1rem;
            animation: profileFadeUp 0.55s ease-out both;
        }

        .profile-card:hover {
            transform: translateY(-3px);
            transition: transform 0.18s ease, box-shadow 0.18s ease;
            box-shadow: 0 24px 44px rgba(37, 99, 235, 0.12);
        }

        .profile-avatar {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            flex-shrink: 0;
            background: linear-gradient(135deg,#6366f1,#8b5cf6);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.6rem;
            font-weight: 700;
            color: #fff;
            animation: profileAvatarFloat 2.8s ease-in-out infinite;
        }

        div[data-testid="stForm"],
        div[data-testid="stAlert"],
        div[data-testid="stHorizontalBlock"] {
            animation: profileFadeUp 0.48s ease-out both;
        }

        div[data-testid="stForm"] {
            border-radius: 16px;
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.98));
            box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
        }

        div[data-testid="stButton"] button,
        div[data-testid="stFormSubmitButton"] button {
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }

        div[data-testid="stButton"] button:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 26px rgba(15, 23, 42, 0.16);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if not is_authenticated():
    login_screen(
        title='Sign in to view your profile',
        description='Use Google or a local account to continue.',
    )
    st.stop()

_inject_profile_styles()

google_logged_in = is_google_logged_in()
local_user = st.session_state.get('local_user')
local_user_name = st.session_state.get('local_user_name', 'User')
guest = is_guest()

st.title('👤 Profile')

pending_toast = st.session_state.pop('profile_toast_message', None)
if pending_toast:
    st.toast(pending_toast)

# --- Guest view ---
if guest:
    st.info(
        'You are browsing as a guest. Create an account to save your wardrobe and preferences.'
    )
    if st.button('Log out (Guest)', type='primary', width='stretch'):
        st.session_state.is_guest = False
        st.session_state.local_user_name = None
        st.rerun()
    st.stop()

# --- Resolve display info ---
if google_logged_in:
    display_email = getattr(st.user, 'email', '') or ''
    display_name = getattr(st.user, 'name', '') or local_user_name or 'Google User'
    provider = 'Google'
else:
    display_email = local_user or ''
    display_name = local_user_name or 'User'
    provider = 'Local'

initials = ''.join(w[0].upper() for w in display_name.split() if w)[:2] or '?'
provider_bg = '#dbeafe' if provider == 'Google' else '#d1fae5'
provider_fg = '#1e40af' if provider == 'Google' else '#065f46'

# --- Profile card ---
st.markdown(
    f"""
    <div class="profile-hero">
        <div class="profile-card">
        <div class="profile-avatar">
            {initials}
        </div>
        <div>
            <div style="font-size:1.2rem;font-weight:700;line-height:1.3;">{display_name}</div>
            <div style="font-size:0.87rem;opacity:0.6;margin-bottom:5px;">{display_email}</div>
            <span style="font-size:0.75rem;font-weight:600;padding:2px 10px;
                         border-radius:999px;background:{provider_bg};color:{provider_fg};">
                {provider}
            </span>
        </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Edit display name (local accounts only) ---
if provider == 'Local':
    st.subheader('Edit Profile')
    with st.form('update_name_form'):
        new_name = st.text_input('Display name', value=display_name)
        save_name = st.form_submit_button('Save', width='stretch')

    if save_name:
        if not new_name.strip():
            st.error('Name cannot be empty.')
        else:
            ok, msg = auth_backend.update_user_name(display_email, new_name.strip())
            if ok:
                st.session_state.local_user_name = new_name.strip()
                st.session_state.profile_toast_message = (
                    f'Display name updated to {new_name.strip()}! ✅'
                )
                st.rerun()
            else:
                st.error(msg)

    # --- Change password ---
    st.subheader('Change Password')
    with st.form('change_password_form'):
        old_pw = st.text_input('Current password', type='password')
        new_pw = st.text_input('New password', type='password')
        confirm_pw = st.text_input('Confirm new password', type='password')
        change_pw = st.form_submit_button('Update password', width='stretch')

    if change_pw:
        if not old_pw:
            st.error('Enter your current password.')
        elif new_pw != confirm_pw:
            st.error('New passwords do not match.')
        else:
            ok, msg = auth_backend.change_password(display_email, old_pw, new_pw)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

elif provider == 'Google':
    st.info('Your name and profile picture are managed by your Google account.')

# --- Logout ---
st.divider()
st.subheader('Account')

if google_logged_in:
    st.button(
        'Log out (Google)',
        on_click=st.logout,
        width='stretch',
        type='primary',
    )
elif local_user:
    if st.button('Log out', width='stretch', type='primary'):
        st.session_state.local_user = None
        st.session_state.local_user_name = None
        st.session_state.is_guest = False
        st.rerun()
