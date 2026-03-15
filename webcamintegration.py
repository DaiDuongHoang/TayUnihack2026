import os
import threading
import streamlit as st
import cv2
import numpy as np
import time
from datetime import datetime


# ---------------------------------------------------------------------------
# Background thread — runs the capture loop independently of Streamlit
# ---------------------------------------------------------------------------
def webcam_stream_thread(cap, placeholder_ref, stop_event):
    """
    Continuously reads frames from `cap` and pushes them to placeholder_ref[0].
    placeholder_ref is a single-element list so the main thread can swap in a
    fresh placeholder after any Streamlit rerun without restarting this thread.
    Stops cleanly when `stop_event` is set.
    """
    while not stop_event.is_set():
        placeholder = placeholder_ref[0]   # always grab the latest live placeholder
        if placeholder is None:
            time.sleep(0.05)
            continue

        ret, frame = cap.read()

        if not ret or frame is None:
            grey = np.full((720, 1280, 3), 180, dtype=np.uint8)
            cv2.putText(
                grey,
                "No signal — check your webcam",
                (340, 360),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (80, 80, 80),
                2,
                cv2.LINE_AA,
            )
            placeholder.image(grey, channels="BGR", use_container_width=True)
        else:
            frame = cv2.resize(frame, (1280, 720))
            placeholder.image(frame, channels="BGR", use_container_width=True)

        time.sleep(1 / 30)  # ~30 FPS


# ---------------------------------------------------------------------------
# Capture a single frame and save it to disk
# ---------------------------------------------------------------------------
def capture_frame():
    """Read one frame from the shared cap object and save it as a JPEG."""
    if not st.session_state.webcam_allowed or st.session_state.cap is None:
        st.toast("Webcam not active. Please allow webcam access first.")
        return

    ret, frame = st.session_state.cap.read()
    if not ret or frame is None:
        st.toast("Unable to capture frame. Please check your webcam.")
        return

    save_dir = os.path.join(os.getcwd(), "captured_frames")
    os.makedirs(save_dir, exist_ok=True)

    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    save_path = os.path.join(save_dir, f"captured_frame_{current_time}.jpg")

    success = cv2.imwrite(save_path, frame)
    if success:
        st.toast(f"✅ Frame saved to: {save_path}")
    else:
        st.toast(f"❌ imwrite failed. Path attempted: {save_path}")


# ---------------------------------------------------------------------------
# Release webcam + stop the background thread
# ---------------------------------------------------------------------------
def release_webcam():
    """Stop the stream thread, release the capture device, reset state."""
    # Signal the thread to stop
    st.session_state.stop_event.set()

    # Wait briefly for the thread to finish
    thread = st.session_state.stream_thread
    if thread is not None and thread.is_alive():
        thread.join(timeout=1)

    # Release the hardware
    if st.session_state.cap is not None:
        st.session_state.cap.release()

    # Reset state
    st.session_state.cap = None
    st.session_state.stream_thread = None


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Webcam Stream", layout="wide")

if "webcam_allowed" not in st.session_state:
    st.session_state.webcam_allowed = False
if "cap" not in st.session_state:
    st.session_state.cap = None
if "stop_event" not in st.session_state:
    st.session_state.stop_event = threading.Event()
if "stream_thread" not in st.session_state:
    st.session_state.stream_thread = None
if "placeholder_ref" not in st.session_state:
    # Single-element list so the background thread can always find
    # the most recently rendered placeholder, even after Streamlit reruns.
    st.session_state.placeholder_ref = [None]

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("📷 Webcam Stream")

# Checkbox — locks itself once ticked
allow_webcam = st.checkbox(
    "Allow webcam",
    value=st.session_state.webcam_allowed,
    disabled=st.session_state.webcam_allowed,
    key="webcam_checkbox",
)

if allow_webcam and not st.session_state.webcam_allowed:
    st.session_state.webcam_allowed = True
    st.rerun()  # one-time rerun just to lock the checkbox — not in the stream loop

# Stop button
if st.session_state.webcam_allowed:
    if st.button("⛔ Stop Webcam"):
        release_webcam()
        st.session_state.webcam_allowed = False
        st.rerun()

st.markdown("### 🎥 Live Feed")
left_col, right_col = st.columns([2, 1])

with left_col:
    frame_placeholder = st.empty()
    # Always point the shared ref at the freshly created placeholder.
    # The background thread reads placeholder_ref[0] each frame, so it
    # automatically switches to this new one after every Streamlit rerun.
    st.session_state.placeholder_ref[0] = frame_placeholder

    if not st.session_state.webcam_allowed:
        # Static grey screen shown before webcam is enabled
        grey = np.full((720, 1280, 3), 180, dtype=np.uint8)
        cv2.putText(
            grey,
            "Webcam not active",
            (460, 360),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (100, 100, 100),
            2,
            cv2.LINE_AA,
        )
        frame_placeholder.image(grey, channels="BGR", use_container_width=True)

    else:
        # Open webcam once
        if st.session_state.cap is None:
            st.session_state.cap = cv2.VideoCapture(0)

        # Start background thread only if it isn't already running
        thread = st.session_state.stream_thread
        if thread is None or not thread.is_alive():
            st.session_state.stop_event.clear()
            new_thread = threading.Thread(
                target=webcam_stream_thread,
                args=(st.session_state.cap, st.session_state.placeholder_ref, st.session_state.stop_event),
                daemon=True,
            )
            new_thread.start()
            st.session_state.stream_thread = new_thread

with right_col:
    st.markdown("### 🛠 Controls")
    if st.button("📸 Capture Frame"):
        capture_frame()