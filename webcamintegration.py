import streamlit as st
import cv2
import numpy as np
import time

st.set_page_config(page_title="Webcam Stream", layout="centered")
st.title("📷 Webcam Stream")

# --- Session state init ---
if "webcam_allowed" not in st.session_state:
    st.session_state.webcam_allowed = False
if "cap" not in st.session_state:
    st.session_state.cap = None


# --- Webcam release function ---
def release_webcam():
    """Release the webcam capture device and reset session state."""
    if st.session_state.cap is not None:
        st.session_state.cap.release()
        st.session_state.cap = None


# --- Checkbox (disabled once ticked) ---
allow_webcam = st.checkbox(
    "Allow webcam",
    value=st.session_state.webcam_allowed,
    disabled=st.session_state.webcam_allowed,
    key="webcam_checkbox",
)

if allow_webcam and not st.session_state.webcam_allowed:
    st.session_state.webcam_allowed = True
    st.rerun()

# --- Stop button (only shown after webcam is allowed) ---
if st.session_state.webcam_allowed:
    if st.button("⛔ Stop Webcam"):
        release_webcam()
        st.session_state.webcam_allowed = False
        st.rerun()

# --- Webcam stream section ---
st.markdown("### 🎥 Live Feed")
frame_placeholder = st.empty()

# Show grey placeholder before webcam is enabled
if not st.session_state.webcam_allowed:
    grey_frame = np.full((480, 640, 3), 180, dtype=np.uint8)
    cv2.putText(
        grey_frame,
        "Webcam not active",
        (160, 250),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (100, 100, 100),
        2,
        cv2.LINE_AA,
    )
    frame_placeholder.image(grey_frame, channels="BGR", use_container_width=True)

# --- Capture loop ---
if st.session_state.webcam_allowed:
    if st.session_state.cap is None:
        st.session_state.cap = cv2.VideoCapture(0)

    cap = st.session_state.cap

    while st.session_state.webcam_allowed:
        ret, frame = cap.read()

        if not ret or frame is None:
            # Webcam disconnected or unavailable — show grey fallback
            grey_frame = np.full((480, 640, 3), 180, dtype=np.uint8)
            cv2.putText(
                grey_frame,
                "No signal — check your webcam",
                (100, 250),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (80, 80, 80),
                2,
                cv2.LINE_AA,
            )
            frame_placeholder.image(
                grey_frame, channels="BGR", use_container_width=True
            )
        else:
            frame_placeholder.image(frame, channels="BGR", use_container_width=True)

        time.sleep(1 / 30)  # ~30 FPS