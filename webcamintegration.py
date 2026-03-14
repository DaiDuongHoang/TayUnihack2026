import cv2
import streamlit as st

@st.dialog("Webcam Integration")
def webcam_integration():
    st.info("This dialog demonstrates webcam integration using OpenCV.")
    run_webcam = st.checkbox("Activate Webcam")

    if run_webcam:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            st.error("Could not access the webcam.")
            return

        stframe = st.empty()
        while run_webcam:
            ret, frame = cap.read()
            if not ret:
                st.error("Failed to capture video.")
                break

            # Convert the frame to RGB format
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            stframe.image(frame_rgb)

        cap.release()