#!/usr/bin/env python3
"""
Run the same weights as the server on validation images and print
per-class detection counts. Use to verify the model predicts all 10 classes.
Run from: object_detection_working/training/
"""
import os
from pathlib import Path
from ultralytics import YOLO

# Same path as server (relative to object_detection_working/)
WEIGHTS = "runs/detect/runs/detect/custom_yolo10/weights/best.pt"
VAL_IMAGES = "dataset/val/images"
CONF = 0.05  # Very low to see all predictions

def main():
    if not os.path.isfile(WEIGHTS):
        print(f"❌ Weights not found: {WEIGHTS}")
        print("Run from object_detection_working/training/")
        return
    if not os.path.isdir(VAL_IMAGES):
        print(f"❌ Val images not found: {VAL_IMAGES}")
        return

    model = YOLO(WEIGHTS)
    print(f"Model classes: {list(model.names.values())}")
    print(f"Running on val images with conf={CONF} (first 15 images)...\n")

    images = sorted(Path(VAL_IMAGES).glob("*.jpg"))[:15]
    total_counts = {}
    for i, img_path in enumerate(images):
        results = model(str(img_path), conf=CONF, imgsz=640, verbose=False)
        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            print(f"  {img_path.name}: no detections")
            continue
        cls_ids = r.boxes.cls.cpu().numpy().astype(int)
        confs = r.boxes.conf.cpu().numpy()
        counts = {}
        for cid, c in zip(cls_ids, confs):
            name = model.names[cid]
            counts[name] = counts.get(name, 0) + 1
            total_counts[name] = total_counts.get(name, 0) + 1
        print(f"  {img_path.name}: {dict(sorted(counts.items()))}")
    print("\n--- Total detections per class (across 15 images) ---")
    for name in model.names.values():
        print(f"  {name}: {total_counts.get(name, 0)}")
    print("\nIf some classes are 0, the model rarely predicts them even at conf=0.05.")

if __name__ == "__main__":
    main()
