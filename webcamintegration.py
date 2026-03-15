import os
import threading
import streamlit as st
import cv2
from datetime import datetime
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

try:
    import av
    from streamlit_webrtc import VideoProcessorBase, WebRtcMode, webrtc_streamer
except ModuleNotFoundError:
    av = None
    VideoProcessorBase = object
    WebRtcMode = None
    webrtc_streamer = None


class SnapshotProcessor(VideoProcessorBase):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest_frame = None

    def recv(self, frame):
        img = frame.to_ndarray(format='bgr24')
        with self._lock:
            self._latest_frame = img.copy()
        return av.VideoFrame.from_ndarray(img, format='bgr24')

    def get_latest_frame(self):
        with self._lock:
            return None if self._latest_frame is None else self._latest_frame.copy()


def open_camera():
    # Try common Windows/OpenCV backends first, then fall back to default.
    backend_candidates = [
        cv2.CAP_DSHOW,
        cv2.CAP_MSMF,
        cv2.CAP_ANY,
    ]

    for backend in backend_candidates:
        cap = cv2.VideoCapture(0, backend)
        if cap is not None and cap.isOpened():
            return cap
        if cap is not None:
            cap.release()

    return None


# ---------------------------------------------------------------------------
# Capture a single frame and save it to disk
# ---------------------------------------------------------------------------
def capture_frame(frame):
    if frame is None:
        st.toast('No webcam frame available yet. Start webcam first.')
        return

    ret, frame = st.session_state.cap.read()
    if not ret or frame is None:
        st.toast("Unable to capture frame. Please check your webcam.")
        return

    save_dir = os.path.join(os.getcwd(), 'captured_frames')
    os.makedirs(save_dir, exist_ok=True)
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    save_path = os.path.join(save_dir, f'captured_frame_{current_time}.jpg')

    success = cv2.imwrite(save_path, frame_to_save)
    st.toast(f'✅ Saved: {save_path}' if success else f'❌ imwrite failed: {save_path}')


st.set_page_config(page_title='Webcam Stream', layout='wide')

if "webcam_allowed" not in st.session_state:
    st.session_state.webcam_allowed = False
if "cap" not in st.session_state:
    st.session_state.cap = None
if "stop_event" not in st.session_state:
    st.session_state.stop_event = threading.Event()
if "stream_thread" not in st.session_state:
    st.session_state.stream_thread = None
if "placeholder_ref" not in st.session_state:
    st.session_state.placeholder_ref = [None]

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title('📷 Webcam Stream')

if webrtc_streamer is None or av is None:
    st.error('streamlit-webrtc is not installed. Run: pip install streamlit-webrtc av')
    st.stop()

st.markdown('### 🎥 Live Feed')
left_col, right_col = st.columns([2, 1])

with left_col:
    frame_placeholder = st.empty()
    # Update the shared pointer every run so the thread always writes
    # to the placeholder that is currently live on screen
    st.session_state.placeholder_ref[0] = frame_placeholder

    if not st.session_state.webcam_allowed:
        grey = np.full((720, 1280, 3), 180, dtype=np.uint8)
        cv2.putText(grey, "Webcam not active", (460, 360),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (100, 100, 100), 2)
        frame_placeholder.image(grey, channels="BGR", use_container_width=True)

    else:
        # Open the capture device exactly once
        if st.session_state.cap is None:
            st.session_state.cap = cv2.VideoCapture(0)

        # Start the background thread exactly once
        thread = st.session_state.stream_thread
        if thread is None or not thread.is_alive():
            st.session_state.stop_event.clear()
            new_thread = threading.Thread(
                target=webcam_stream_thread,
                args=(
                    st.session_state.cap,
                    st.session_state.placeholder_ref,
                    st.session_state.stop_event,
                ),
                daemon=True,
            )
            new_thread.start()
            st.session_state.stream_thread = new_thread

with right_col:
    st.markdown('### 🛠 Controls')
    st.caption(
        'Use Start/Stop on the webcam widget. If camera disappears, press Restart Camera.'
    )

    if st.button('🔄 Restart Camera', width='stretch'):
        st.session_state.webcam_instance += 1
        st.toast('Camera restarted.')
        st.rerun()

    if st.button('📸 Capture Frame'):
        frame = None
        if webrtc_ctx.video_processor:
            frame = webrtc_ctx.video_processor.get_latest_frame()
        capture_frame(frame)

    if not webrtc_ctx.state.playing:
        st.info('Camera is idle. Click Start above to begin live preview.')
