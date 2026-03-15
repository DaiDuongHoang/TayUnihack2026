import os
import threading
import streamlit as st
import cv2
from datetime import datetime

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


# ---------------------------------------------------------------------------
# Capture a single frame and save it to disk
# ---------------------------------------------------------------------------
def capture_frame(frame):
    if frame is None:
        st.toast('No webcam frame available yet. Start webcam first.')
        return

    frame_to_save = frame.copy()

    save_dir = os.path.join(os.getcwd(), 'captured_frames')
    os.makedirs(save_dir, exist_ok=True)
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    save_path = os.path.join(save_dir, f'captured_frame_{current_time}.jpg')

    success = cv2.imwrite(save_path, frame_to_save)
    st.toast(f'✅ Saved: {save_path}' if success else f'❌ imwrite failed: {save_path}')


st.set_page_config(page_title='Webcam Stream', layout='wide')

if 'webcam_instance' not in st.session_state:
    st.session_state.webcam_instance = 1

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
    webrtc_ctx = webrtc_streamer(
        key=f'stable-webcam-{st.session_state.webcam_instance}',
        mode=WebRtcMode.SENDRECV,
        media_stream_constraints={
            'video': {
                'width': {'ideal': 1280, 'max': 1920},
                'height': {'ideal': 720, 'max': 1080},
                'frameRate': {'ideal': 30, 'max': 30},
            },
            'audio': False,
        },
        video_processor_factory=SnapshotProcessor,
        async_processing=False,
        video_html_attrs={
            'autoPlay': True,
            'controls': False,
            'muted': True,
            'style': {'width': '100%', 'maxWidth': '1280px', 'borderRadius': '12px'},
        },
    )

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
