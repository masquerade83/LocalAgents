#!/usr/bin/env python3
"""
Convert COCO-format annotations (JSON) to YOLO-format .txt label files.
Use this when your labeling tool exports COCO (e.g. Roboflow, Label Studio, CVAT).

Usage:
  # Single COCO JSON → train labels
  python3 coco_to_yolo.py path/to/annotations.json train

  # Two COCO JSONs for train and val
  python3 coco_to_yolo.py path/to/train_annotations.json train
  python3 coco_to_yolo.py path/to/val_annotations.json val

  # Use a custom class list (optional; default: from dataset/dataset.yaml)
  python3 coco_to_yolo.py annotations.json train --classes person bottle book
"""

import json
import argparse
from pathlib import Path

DATASET_DIR = Path("dataset")
YAML_PATH = DATASET_DIR / "dataset.yaml"


def load_class_names():
    """Load class names from dataset.yaml (order = YOLO class_id)."""
    if not YAML_PATH.exists():
        return ["person", "bottle", "book"]  # fallback
    try:
        import yaml
        with open(YAML_PATH) as f:
            data = yaml.safe_load(f)
        names = data.get("names", ["person", "bottle", "book"])
        return names if isinstance(names, list) else ["person", "bottle", "book"]
    except Exception:
        return ["person", "bottle", "book"]


def coco_to_yolo_bbox(bbox, img_w, img_h):
    """Convert COCO bbox [x, y, width, height] (absolute) to YOLO [cx, cy, w, h] (normalized)."""
    x, y, w, h = bbox
    if img_w <= 0 or img_h <= 0:
        return None
    cx = (x + w / 2) / img_w
    cy = (y + h / 2) / img_h
    nw = w / img_w
    nh = h / img_h
    # clamp to [0, 1]
    cx = max(0, min(1, cx))
    cy = max(0, min(1, cy))
    nw = max(0, min(1, nw))
    nh = max(0, min(1, nh))
    return cx, cy, nw, nh


def run(coco_path: Path, split: str, class_names: list):
    assert split in ("train", "val"), "split must be 'train' or 'val'"
    labels_dir = DATASET_DIR / split / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)

    with open(coco_path) as f:
        coco = json.load(f)

    images_by_id = {im["id"]: im for im in coco.get("images", [])}
    categories = {c["id"]: c["name"] for c in coco.get("categories", [])}
    # Map category name -> YOLO class index
    name_to_idx = {name: i for i, name in enumerate(class_names)}

    # Build annotations per image
    anns_by_image = {}
    for ann in coco.get("annotations", []):
        img_id = ann["image_id"]
        if img_id not in anns_by_image:
            anns_by_image[img_id] = []
        anns_by_image[img_id].append(ann)

    written = 0
    for img_id, im in images_by_id.items():
        file_name = im.get("file_name", "")
        img_w = im.get("width", 1)
        img_h = im.get("height", 1)
        stem = Path(file_name).stem
        anns = anns_by_image.get(img_id, [])

        lines = []
        for ann in anns:
            cat_id = ann.get("category_id")
            cat_name = categories.get(cat_id, "")
            if cat_name not in name_to_idx:
                continue
            class_idx = name_to_idx[cat_name]
            bbox = ann.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            yolo_bbox = coco_to_yolo_bbox(bbox, img_w, img_h)
            if yolo_bbox is None:
                continue
            cx, cy, nw, nh = yolo_bbox
            lines.append(f"{class_idx} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

        out_path = labels_dir / f"{stem}.txt"
        with open(out_path, "w") as f:
            f.write("\n".join(lines))
        written += 1

    print(f"Wrote {written} label files to {labels_dir}")
    return written


def main():
    ap = argparse.ArgumentParser(description="Convert COCO JSON to YOLO .txt labels")
    ap.add_argument("coco_json", type=Path, help="Path to COCO annotations.json")
    ap.add_argument("split", choices=["train", "val"], help="Target split: train or val")
    ap.add_argument("--classes", nargs="+", default=None, help="Class names in order (default: from dataset.yaml)")
    args = ap.parse_args()

    if not args.coco_json.exists():
        print(f"File not found: {args.coco_json}")
        return 1

    class_names = args.classes if args.classes else load_class_names()
    print(f"Classes: {class_names}")
    run(args.coco_json, args.split, class_names)
    return 0


if __name__ == "__main__":
    exit(main())
