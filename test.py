import os
from pathlib import Path

import torch
from ultralytics import YOLO

category_path = Path("models/best_category_cls.pt")
color_path = Path("models/best_color_cls.pt")
if __name__ == "__main__":
    model = YOLO(str(category_path))
    results = model.predict("test.jpg", device="cpu")
    pred = results[0]

    top1_idx = int(pred.probs.top1)
    top1_label = pred.names[top1_idx]
    top1_conf = float(pred.probs.top1conf)

    print(f"Predicted Category: {top1_label} (Confidence: {top1_conf:.2f})")

    model = YOLO(str(color_path))
    results = model.predict("test.jpg", device="cpu")
    pred = results[0]
    top1_idx = int(pred.probs.top1)
    top1_label = pred.names[top1_idx]
    top1_conf = float(pred.probs.top1conf)
    print(f"Predicted Color: {top1_label} (Confidence: {top1_conf:.2f})")
