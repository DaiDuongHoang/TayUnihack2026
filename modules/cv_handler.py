"""
cv_handler.py – Image processing and clothing classification logic.

TODO (team): Replace the placeholder logic with a real YOLO-based pipeline.

Workflow
--------
1. load_image        – read an uploaded file into a NumPy array via OpenCV.
2. detect_clothing   – run YOLO inference and return detected clothing items.
3. classify_item     – map a detection to a high-level wardrobe category.
"""

from __future__ import annotations

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Optional YOLO model – loaded lazily so the app starts even without a GPU.
# ---------------------------------------------------------------------------
_model = None  # type: ignore[assignment]


def _get_model():
    """Load the YOLO model once and cache it in the module-level variable."""
    global _model
    if _model is None:
        try:
            from ultralytics import YOLO  # noqa: PLC0415

            # TODO (team): replace with your fine-tuned clothing model path.
            _model = YOLO("yolov8n.pt")
        except (ImportError, ModuleNotFoundError) as exc:
            raise RuntimeError(
                "Could not import 'ultralytics'. "
                "Ensure it is installed: pip install ultralytics"
            ) from exc
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Could not load YOLO model weights. "
                "Ensure the model file is available."
            ) from exc
    return _model


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_image(uploaded_file) -> np.ndarray:
    """Decode a Streamlit UploadedFile (or any bytes-like object) into BGR ndarray."""
    file_bytes = np.frombuffer(uploaded_file.read(), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode the uploaded image.")
    return image


def detect_clothing(image: np.ndarray) -> list[dict]:
    """
    Run object detection on *image* and return a list of detected items.

    Each item is a dict::

        {
            "label": str,        # e.g. "shirt"
            "confidence": float, # 0.0 – 1.0
            "bbox": list[int],   # [x1, y1, x2, y2]
        }

    TODO (team): Wire up _get_model() and parse the real YOLO results.
    """
    # --- PLACEHOLDER ---
    # Replace the block below with actual YOLO inference, for example:
    #
    #   model = _get_model()
    #   results = model(image)
    #   detections = []
    #   for box in results[0].boxes:
    #       detections.append({
    #           "label": model.names[int(box.cls)],
    #           "confidence": float(box.conf),
    #           "bbox": box.xyxy[0].tolist(),
    #       })
    #   return detections
    return [
        {"label": "shirt", "confidence": 0.91, "bbox": [50, 30, 200, 250]},
        {"label": "jeans", "confidence": 0.87, "bbox": [60, 260, 190, 480]},
    ]


def classify_item(label: str) -> str:
    """
    Map a raw detection label to a high-level wardrobe category.

    Returns one of: "top", "bottom", "outerwear", "shoes", "accessory", "unknown".

    TODO (team): Extend the mapping as your model vocabulary grows.
    """
    tops = {"shirt", "t-shirt", "blouse", "sweater", "hoodie", "tank top"}
    bottoms = {"jeans", "trousers", "shorts", "skirt", "pants"}
    outerwear = {"jacket", "coat", "blazer", "cardigan"}
    shoes = {"shoes", "boots", "sneakers", "sandals", "heels"}
    accessories = {"hat", "scarf", "bag", "belt", "glasses"}

    label_lower = label.lower()
    if label_lower in tops:
        return "top"
    if label_lower in bottoms:
        return "bottom"
    if label_lower in outerwear:
        return "outerwear"
    if label_lower in shoes:
        return "shoes"
    if label_lower in accessories:
        return "accessory"
    return "unknown"
