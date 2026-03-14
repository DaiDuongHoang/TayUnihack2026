import streamlit as st


@st.dialog("Add a new clothe item")
def add_clothe_item():
    uploaded_files = st.file_uploader(
        "Upload image(s) of the clothe item",
        type=["jpg", "jpeg", "png", "bmp"],
        help="Supported formats: JPG, JPEG, PNG, BMP. Max file size: 10MB.",
        accept_multiple_files=True,
    )

    has_uploaded_files = bool(uploaded_files)
    manual_cloth_type = None
    manual_color = None

    if has_uploaded_files:
        for file in uploaded_files:
            st.image(file, caption=file.name)
        st.success(f"Successfully uploaded {len(uploaded_files)} file(s)!")
    else:
        st.info("Upload an image, or enter the clothe details manually to continue.")

        manual_cloth_type = st.selectbox(
            "**Clothe Type**",
            [
                "👕 T-Shirt",
                "🧥 Blazer",
                "👗 Dress",
                "🧥 Jacket",
                "🥼 Coat",
                "🧥 Hoodie",
                "🧶 Sweater",
                "🩲 Shorts",
                "👗 Skirt",
                "👖 Jeans",
                "👖 Pants",
            ],
            index=None,
            placeholder="Select a clothe type",
            help="Select the type of clothe item",
        )

        manual_color = st.color_picker(
            "**Color**", help="Choose the color of the clothe item", width="stretch"
        )

    manual_entry_ready = manual_cloth_type is not None and manual_color is not None

    if has_uploaded_files or manual_entry_ready:
        if st.button("Submit", type="primary", use_container_width=True):
            if has_uploaded_files:
                st.success("Clothe item submitted successfully.")
            else:
                st.success(
                    f"Manual entry submitted for a {manual_cloth_type} item in {manual_color}."
                )


danger_button = st.components.v2.component(
    name="hold_to_confirm",
    html="""
<button id="danger-btn" class="hold-button">
    <svg class="progress-ring" viewBox="0 0 100 100">
    <circle class="ring-bg" cx="50" cy="50" r="45" />
    <circle id="ring-progress" class="ring-progress" cx="50" cy="50" r="45" />
    </svg>
    <div class="button-content">
    <span id="icon" class="icon">🗑️</span>
    <span id="label" class="label">Hold to Delete</span>
    </div>
</button>
""",
    css="""
.hold-button {
    position: relative;
    width: 7.5rem;
    height: 7.5rem;
    padding: 0 2rem;
    border-radius: 50%;
    border: 1px solid var(--st-primary-color);
    background: var(--st-secondary-background-color);
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.hold-button:hover {
    transform: scale(1.05);
    border-color: var(--st-red-color);
}

.hold-button:active:not(:disabled) {
    transform: scale(0.98);
}

.hold-button:disabled {
    cursor: not-allowed;
    opacity: 0.9;
}

.hold-button.holding {
    animation: pulse 0.5s ease-in-out infinite;
    border-color: var(--st-red-color);
}

.hold-button.triggered {
    animation: success-burst 0.6s ease-out forwards;
}

@keyframes pulse {
    0%,
    100% {
    box-shadow: 0 0 0 0 var(--st-red-color);
    }
    50% {
    box-shadow: 0 0 0 15px transparent;
    }
}

@keyframes success-burst {
    0% {
    transform: scale(1);
    }
    50% {
    transform: scale(1.15);
    background: var(--st-red-background-color);
    }
    100% {
    transform: scale(1);
    }
}

.progress-ring {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    transform: rotate(-90deg);
}

.ring-bg {
    fill: none;
    stroke: var(--st-border-color);
    stroke-width: 4;
}

.ring-progress {
    fill: none;
    stroke: var(--st-red-color);
    stroke-width: 4;
    stroke-linecap: round;
    stroke-dasharray: 283;
    stroke-dashoffset: 283;
    transition: stroke-dashoffset 0.1s linear;
    filter: drop-shadow(0 0 0.5rem var(--st-red-color));
}

.button-content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    font-family: var(--st-font);
}

.icon {
    font-size: 2rem;
    transition: transform 0.3s ease;
}

.hold-button:hover .icon {
    transform: scale(1.1);
}

.hold-button.holding .icon {
    animation: shake 0.15s ease-in-out infinite;
}

@keyframes shake {
    0%,
    100% {
    transform: translateX(0);
    }
    25% {
    transform: translateX(-2px) rotate(-5deg);
    }
    75% {
    transform: translateX(2px) rotate(5deg);
    }
}

.label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--st-text-color);
    opacity: 0.6;
    transition: all 0.3s ease;
}

.hold-button.holding .label {
    color: var(--st-red-color);
    opacity: 1;
}

.hold-button.triggered .icon,
.hold-button.triggered .label {
    color: var(--st-primary-color);
    opacity: 1;
}
""",
    js="""
const HOLD_DURATION = 2000; // 2 seconds
const COOLDOWN_DURATION = 1500; // cooldown after trigger
const CIRCUMFERENCE = 2 * Math.PI * 45; // circle circumference

export default function ({ parentElement, setTriggerValue, data }) {
    const button = parentElement.querySelector("#danger-btn");
    const progress = parentElement.querySelector("#ring-progress");
    const icon = parentElement.querySelector("#icon");
    const label = parentElement.querySelector("#label");

    let startTime = null;
    let animationFrame = null;
    let isDisabled = false; // Prevent interaction during cooldown

    function updateProgress() {
    if (!startTime) return;

    const elapsed = Date.now() - startTime;
    const progressPercent = Math.min(elapsed / HOLD_DURATION, 1);
    const offset = CIRCUMFERENCE * (1 - progressPercent);

    progress.style.strokeDashoffset = offset;

    if (progressPercent >= 1) {
        // Triggered!
        triggerAction();
    } else {
        animationFrame = requestAnimationFrame(updateProgress);
    }
    }

    function startHold() {
    if (isDisabled) return; // Ignore if in cooldown

    startTime = Date.now();
    button.classList.add("holding");
    label.textContent = data?.continue ?? "Keep holding...";
    animationFrame = requestAnimationFrame(updateProgress);
    }

    function cancelHold() {
    if (isDisabled) return; // Ignore if in cooldown

    startTime = null;
    button.classList.remove("holding");
    label.textContent = data?.start ?? "Hold to Delete";
    progress.style.strokeDashoffset = CIRCUMFERENCE;

    if (animationFrame) {
        cancelAnimationFrame(animationFrame);
        animationFrame = null;
    }
    }

    function triggerAction() {
    cancelAnimationFrame(animationFrame);
    animationFrame = null;
    startTime = null;
    isDisabled = true; // Disable during cooldown

    button.classList.remove("holding");
    button.classList.add("triggered");
    button.disabled = true;

    icon.textContent = "✓";
    label.textContent = data?.completed ?? "Deleted!";
    progress.style.strokeDashoffset = 0;

    // Send trigger to Python
    setTriggerValue("confirmed", true);

    // Reset after cooldown
    setTimeout(() => {
        button.classList.remove("triggered");
        button.disabled = false;
        isDisabled = false;
        icon.textContent = data?.icon ?? "🗑️";
        label.textContent = data?.start ?? "Hold to Delete";
        progress.style.strokeDashoffset = CIRCUMFERENCE;
    }, COOLDOWN_DURATION);
    }

    function handleTouchStart(e) {
    e.preventDefault();
    startHold();
    }

    // Mouse events
    button.addEventListener("mousedown", startHold);
    button.addEventListener("mouseup", cancelHold);
    button.addEventListener("mouseleave", cancelHold);
    button.addEventListener("contextmenu", cancelHold); // Ctrl+Click on Mac

    // Touch events for mobile
    button.addEventListener("touchstart", handleTouchStart);
    button.addEventListener("touchend", cancelHold);
    button.addEventListener("touchcancel", cancelHold);

    return () => {
    if (animationFrame) cancelAnimationFrame(animationFrame);

    // Remove mouse event listeners
    button.removeEventListener("mousedown", startHold);
    button.removeEventListener("mouseup", cancelHold);
    button.removeEventListener("mouseleave", cancelHold);
    button.removeEventListener("contextmenu", cancelHold);

    // Remove touch event listeners
    button.removeEventListener("touchstart", handleTouchStart);
    button.removeEventListener("touchend", cancelHold);
    button.removeEventListener("touchcancel", cancelHold);
    };
}
""",
)
st.title("Hold-to-Confirm Button")
st.caption("A dangerous action that requires intentional confirmation")


if __name__ == "__main__":
    if st.button("Add Clothe Item", type="primary"):
        add_clothe_item()
