from pathlib import Path

from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
TEST_IMAGE_PATH = BASE_DIR / "tay.jpg"


def _resolve_existing_path(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    checked = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"None of the expected files were found: {checked}")


def _predict_top1(model_path: Path, image_path: Path, label_title: str) -> None:
    model = YOLO(str(model_path))
    results = model.predict(str(image_path), device="cpu")
    pred = results[0]

    if pred.probs is None:
        raise RuntimeError(
            f"No classification probabilities returned for model: {model_path}"
        )

    top1_idx = int(pred.probs.top1)
    top1_label = pred.names[top1_idx]
    top1_conf = float(pred.probs.top1conf)
    print(f"Predicted {label_title}: {top1_label} (Confidence: {top1_conf:.2f})")


if __name__ == "__main__":
    category_model_path = _resolve_existing_path(MODELS_DIR / "best_category_cls.pt")
    color_model_path = _resolve_existing_path(
        MODELS_DIR / "best_color_cls.pt",
        MODELS_DIR / "bestcolor_cls.pt",
    )
    image_path = _resolve_existing_path(TEST_IMAGE_PATH)

    _predict_top1(category_model_path, image_path, "Category")
    _predict_top1(color_model_path, image_path, "Color")
