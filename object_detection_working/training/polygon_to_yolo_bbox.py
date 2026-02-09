#!/usr/bin/env python3
"""
Convert polygon-format label files (class_id x1 y1 x2 y2 x3 y3 ...) to YOLO bbox format
(class_id cx cy w h, normalized 0-1). Overwrites .txt files in place.
Run from training/ with: python3 polygon_to_yolo_bbox.py
"""

from pathlib import Path
import cv2

DATASET_DIR = Path("dataset")


def polygon_to_bbox_xyxy(values):
    """values = [class_id, x1, y1, x2, y2, ...]. Returns (class_id, x_min, y_min, x_max, y_max) normalized."""
    if len(values) < 5:
        return None
    try:
        class_id = int(float(values[0]))
        coords = [float(x) for x in values[1:]]
        if len(coords) % 2 != 0:
            return None
        xs = coords[0::2]
        ys = coords[1::2]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        return (class_id, x_min, y_min, x_max, y_max)
    except (ValueError, IndexError):
        return None


def xyxy_to_yolo_line(class_id, x_min, y_min, x_max, y_max, nc=3):
    """Convert to normalized center + size (YOLO format). Clamp class_id to 0..nc-1."""
    class_id = max(0, min(nc - 1, int(class_id)))
    cx = (x_min + x_max) / 2
    cy = (y_min + y_max) / 2
    w = x_max - x_min
    h = y_max - y_min
    return f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def is_yolo_bbox_line(line):
    """Check if line is already YOLO bbox (exactly 5 values)."""
    parts = line.strip().split()
    if len(parts) != 5:
        return False
    try:
        c, x, y, w, h = [float(p) for p in parts]
        return 0 <= x <= 1 and 0 <= y <= 1 and 0 <= w <= 1 and 0 <= h <= 1
    except ValueError:
        return False


def clamp_class_ids_in_file(txt_path: Path, nc: int = 3) -> bool:
    """Ensure all class IDs are in 0..nc-1. Returns True if changed."""
    content = txt_path.read_text()
    new_lines = []
    changed = False
    for line in content.strip().splitlines():
        parts = line.strip().split()
        if len(parts) != 5:
            new_lines.append(line)
            continue
        try:
            c = int(float(parts[0]))
            c_new = max(0, min(nc - 1, c))
            if c != c_new:
                changed = True
            new_lines.append(f"{c_new} {' '.join(parts[1:])}")
        except (ValueError, IndexError):
            new_lines.append(line)
    if new_lines:
        txt_path.write_text("\n".join(new_lines) + "\n")
    return changed


def process_label_file(txt_path: Path, img_dir: Path) -> bool:
    """Convert polygon lines to YOLO bbox. If already 5 values, keep. Returns True if changed."""
    stem = txt_path.stem
    # Find corresponding image for dimensions (optional; we use normalized coords so not strictly needed)
    img_path = None
    for ext in (".jpg", ".jpeg", ".png"):
        p = img_dir / f"{stem}{ext}"
        if p.exists():
            img_path = p
            break
    content = txt_path.read_text()
    new_lines = []
    changed = False
    for line in content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if is_yolo_bbox_line(line):
            new_lines.append(line)
            continue
        # Polygon or other multi-value format
        parsed = polygon_to_bbox_xyxy(parts)
        if parsed is None:
            continue
        class_id, x_min, y_min, x_max, y_max = parsed
        new_lines.append(xyxy_to_yolo_line(class_id, x_min, y_min, x_max, y_max, nc=3))
        changed = True
    if new_lines:
        txt_path.write_text("\n".join(new_lines) + "\n")
    return changed


def main():
    nc = 3  # number of classes in dataset.yaml
    for split in ("train", "val"):
        lbl_dir = DATASET_DIR / split / "labels"
        img_dir = DATASET_DIR / split / "images"
        if not lbl_dir.exists():
            continue
        count = 0
        for txt_path in lbl_dir.glob("*.txt"):
            if process_label_file(txt_path, img_dir):
                count += 1
        print(f"{split}: converted {count} label files to YOLO bbox format")
        # Clamp class IDs to 0..nc-1
        clamp_count = 0
        for txt_path in lbl_dir.glob("*.txt"):
            if clamp_class_ids_in_file(txt_path, nc):
                clamp_count += 1
        if clamp_count:
            print(f"{split}: clamped class IDs to 0..{nc-1} in {clamp_count} files")
    print("Done. Re-run training.")


if __name__ == "__main__":
    main()
