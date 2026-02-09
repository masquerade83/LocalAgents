#!/usr/bin/env python3
"""
Update dataset/dataset.yaml to match class IDs found in label files.
- Sets nc = max(class_id) + 1
- Keeps existing names for indices 0..nc-1; pads with class_0, class_1, ... if needed.
Run from training/:  python3 sync_classes_from_labels.py
"""

import yaml
from pathlib import Path

DATASET_DIR = Path("dataset")
YAML_PATH = DATASET_DIR / "dataset.yaml"


def get_class_ids_from_labels():
    """Return sorted set of class IDs found in train/val labels."""
    ids = set()
    for split in ("train", "val"):
        lbl_dir = DATASET_DIR / split / "labels"
        if not lbl_dir.exists():
            continue
        for f in lbl_dir.glob("*.txt"):
            for line in f.read_text().strip().splitlines():
                parts = line.strip().split()
                if len(parts) >= 1:
                    try:
                        ids.add(int(parts[0]))
                    except ValueError:
                        pass
    return sorted(ids)


def main():
    ids = get_class_ids_from_labels()
    if not ids:
        print("No class IDs found in labels. Leaving dataset.yaml unchanged.")
        return
    nc = max(ids) + 1
    print(f"Class IDs in labels: {ids} -> nc = {nc}")

    # Load current yaml
    if YAML_PATH.exists():
        with open(YAML_PATH) as f:
            data = yaml.safe_load(f)
    else:
        data = {"path": str(DATASET_DIR.resolve()), "train": "train/images", "val": "val/images", "test": "test/images"}

    current_names = data.get("names", [])
    if isinstance(current_names, dict):
        current_names = [current_names.get(i, f"class_{i}") for i in range(max(current_names.keys()) + 1)] if current_names else []
    names = list(current_names)
    # Pad or trim to length nc
    while len(names) < nc:
        names.append(f"class_{len(names)}")
    names = names[:nc]
    data["nc"] = nc
    data["names"] = names

    with open(YAML_PATH, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    print(f"Updated {YAML_PATH}: nc={nc}, names={names}")


if __name__ == "__main__":
    main()
