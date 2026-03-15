import os
import threading
import streamlit as st
import cv2
from datetime import datetime
from wardrobe import addclothemedia

css = """
<style>
/* Gradient box container */
.st-key-gradient-box {
    background: linear-gradient(90deg, #1a1a2e, #16213e, #0f3460);
    color: white;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
}
.st-key-gradient-box h1 {
    color: white !important;
    font-size: 2.5rem;
    margin: 0;
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) 0.05s both;
}

/* Description container */
.st-key-description-box {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) 0.2s both;
}

/* Target text elements inside description box */
.st-key-description-box p,
.st-key-description-box li,
.st-key-description-box strong {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) 0.3s both;
}

@keyframes fadeSlideDownSettle {
    0% {
        opacity: 0;
        transform: translateY(-20px);
    }
    60% {
        opacity: 1;
        transform: translateY(4px);   /* subtle slide UP past resting point */
    }
    100% {
        opacity: 1;
        transform: translateY(0);     /* settles back to natural position */
    }
}

.webcam-title {
    margin: 0;
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
}

div[data-testid="stButton"] button {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

div[data-testid="stButton"] button:hover {
    transform: translateY(-3px);
    box-shadow: 0px 10px 22px rgba(0, 0, 0, 0.28);
}

div[data-testid="stColumn"] {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
}

div[data-testid="stDivider"] {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) 0.3s both;
}

div[data-testid="stAlert"] {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
}

div[data-testid="stButton"]:nth-child(1) button { animation-delay: 0.0s; }
div[data-testid="stButton"]:nth-child(2) button { animation-delay: 0.1s; }
div[data-testid="stButton"]:nth-child(3) button { animation-delay: 0.2s; }
div[data-testid="stButton"]:nth-child(4) button { animation-delay: 0.3s; }
</style>
<script>
(() => {
    const controlFont = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif";

    const applyToDoc = (doc) => {
        if (!doc) {
            return;
        }

        let styleTag = doc.getElementById('taylr-webrtc-font-style');
        if (!styleTag) {
            styleTag = doc.createElement('style');
            styleTag.id = 'taylr-webrtc-font-style';
            styleTag.textContent = `
                button,
                select,
                option,
                label {
                    font-family: ${controlFont} !important;
                    font-weight: 600 !important;
                    letter-spacing: 0.01em !important;
                }
            `;
            doc.head.appendChild(styleTag);
        }
    };

    const tryApply = () => {
        const frames = Array.from(document.querySelectorAll('iframe'));
        for (const frame of frames) {
            const fingerprint = `${frame.title || ''} ${frame.id || ''} ${frame.src || ''}`.toLowerCase();
            if (!/(webrtc|streamlit|component)/.test(fingerprint)) {
                continue;
            }

            try {
                const frameDoc = frame.contentDocument || frame.contentWindow?.document;
                applyToDoc(frameDoc);
            } catch (_) {
                // Best-effort only; cross-origin/sandboxed frames may block access.
            }
        }
    };

    tryApply();
    const observer = new MutationObserver(tryApply);
    observer.observe(document.body, { childList: true, subtree: true });
    window.setInterval(tryApply, 1200);
})();
</script>
"""
st.html(css)

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
    filename = f'captured_frame_{current_time}.jpg'
    save_path = os.path.join(save_dir, filename)

    success = cv2.imwrite(save_path, frame_to_save)
    st.toast(f'✅ Saved: {save_path}' if success else f'❌ imwrite failed: {save_path}')
    if success:
        st.image(frame_to_save, caption='Captured Frame', use_column_width=True)
        local_email = st.session_state.get('local_user')
        clean_item_name = filename.strip(".*jpg|jpeg|png|webp")

        addclothemedia(frame_to_save, clean_item_name, local_email)

st.set_page_config(page_title='Webcam Stream', layout='wide')

if 'webcam_instance' not in st.session_state:
    st.session_state.webcam_instance = 1

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.markdown('<h1 class="webcam-title">📷 Webcam Stream</h1>', unsafe_allow_html=True)

if webrtc_streamer is None or av is None:
    st.error('streamlit-webrtc is not installed. Run: pip install streamlit-webrtc av')
    st.stop()

st.divider()

left_col, right_col = st.columns([2, 1])

with left_col:
    st.markdown('### 🎥 Live Feed')
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

    if st.button('📸 Capture Frame', width='stretch'):
        frame = None
        if webrtc_ctx.video_processor:
            frame = webrtc_ctx.video_processor.get_latest_frame()
        capture_frame(frame)

    if not webrtc_ctx.state.playing:
        st.info('Camera is idle. Click Start above to begin live preview.')