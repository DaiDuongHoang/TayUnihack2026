import os

import streamlit as st
import cv2
import numpy as np
import time
from datetime import datetime

def capture_frame():
    if st.session_state.webcam_allowed and st.session_state.cap is not None:
        ret, frame = st.session_state.cap.read()
        if ret and frame is not None:
            # Build the folder path relative to the script's location
            save_dir = os.path.join(os.path.dirname(__file__), "captured_frames")
            os.makedirs(save_dir, exist_ok=True)  # exist_ok avoids errors if folder already exists

            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            save_path = os.path.join(save_dir, f"captured_frame_{current_time}.jpg")

            success = cv2.imwrite(save_path, frame)
            if success:
                st.toast(f"Frame saved!")
            else:
                st.toast("imwrite failed — check the path or file format.")
        else:
            st.toast("Unable to capture frame. Please check your webcam.")
    else:
        st.toast("Webcam not active. Please allow webcam access first.")

st.set_page_config(page_title="Webcam Stream", layout="wide")
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

# --- Webcam stream section ---
st.markdown("### 🎥 Live Feed")
st.set_page_config(layout="wide")
left_col, right_col = st.columns([2, 1])  # left takes 2/3 of the width, rest is empty space

with left_col:
    frame_placeholder = st.empty()

# Show grey placeholder before webcam is enabled
if not st.session_state.webcam_allowed:
    grey_frame = np.full((720, 1280, 3), 180, dtype=np.uint8)  # height x width
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
    ret, frame = cap.read()

    if not ret or frame is None:
        # Webcam disconnected or unavailable — show grey fallback
        grey_frame = np.full((720, 1280, 3), 180, dtype=np.uint8)
        cv2.putText(
            grey_frame,
            "No signal — check your webcam",
            (160, 250),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (80, 80, 80),
            2,
            cv2.LINE_AA,
        )
        frame_placeholder.image(grey_frame, channels="BGR", use_container_width=True)
    else:
        frame_placeholder.image(frame, channels="BGR", use_container_width=True)

# --- Capture current frame ---
with right_col:
    if st.button("Capture Frame"):
        capture_frame()

# Rerun to refresh the live feed (~30 FPS)
if st.session_state.webcam_allowed:
    time.sleep(1 / 30)
    st.rerun()
