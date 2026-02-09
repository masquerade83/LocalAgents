# Re-annotate from scratch

Your **train** and **val** images have no labels. Follow these steps to label them and plug labels back in.

---

## Step 1: Create zip files for upload

From the `training` folder:

```bash
cd /Users/shailja/clawd/object_detection_working/training
python3 quick_label_helper.py
```

This creates:

- **train_images_for_labeling.zip** (167 images)
- **val_images_for_labeling.zip** (58 images)

Keep these in the `training` folder (or move to Downloads); you’ll upload them to the labeling site.

---

## Step 2: Label on makesense.ai

1. Open **https://www.makesense.ai/**
2. Click **Get started** and upload **train_images_for_labeling.zip**.
3. Choose **Object detection**.
4. **Add labels**: use the same class names as in your dataset:
   - `person`
   - `bottle`
   - `book`
5. For each image:
   - Draw a box around each object.
   - Assign the correct label.
   - Save / go to next image.
6. When done: **Actions → Export annotations**.
7. Select **YOLO** format and download the zip (e.g. `annotations.zip`).

---

## Step 3: Put train labels in the project

From the `training` folder, run (use the path to the zip you downloaded, e.g. from Downloads):

```bash
cd /Users/shailja/clawd/object_detection_working/training
python3 quick_label_helper.py ~/Downloads/annotations.zip train
```

This copies all `.txt` files from the zip into **dataset/train/labels/** so each image has a matching label file (e.g. `frame_000001.jpg` ↔ `frame_000001.txt`).

---

## Step 4: Label validation set

1. In makesense.ai, start a **new project** (or clear the current one).
2. Upload **val_images_for_labeling.zip** (58 images).
3. Use the **same labels**: `person`, `bottle`, `book`.
4. Annotate all val images.
5. **Export → YOLO** and download (e.g. `val_annotations.zip`).

---

## Step 5: Put val labels in the project

```bash
cd /Users/shailja/clawd/object_detection_working/training
python3 quick_label_helper.py ~/Downloads/val_annotations.zip val
```

Labels go into **dataset/val/labels/**.

---

## Step 6: Check and train

Check that image/label names match:

```bash
cd /Users/shailja/clawd/object_detection_working/training
python3 -c "
from pathlib import Path
for split in ('train', 'val'):
    imgs = set(f.stem for f in (Path('dataset')/split/'images').iterdir() if f.suffix.lower() in ('.jpg','.png'))
    lbls = set(f.stem for f in (Path('dataset')/split/'labels').iterdir() if f.suffix=='.txt')
    print(f'{split}: {len(imgs)} images, {len(lbls)} labels, {len(imgs&lbls)} matched')
"
```

Then train:

```bash
python3 train_custom_model.py
```

---

## Class names (must match)

Use exactly these in the labeling tool and in **dataset/dataset.yaml**:

- **person**
- **bottle**
- **book**

Spelling and case must match so the trained model and viewer use the same classes.

---

## COCO-format annotations

If your tool exports **COCO** (one JSON with `images`, `annotations`, `categories`) instead of YOLO `.txt` files:

1. Export annotations as **COCO JSON** from your tool (e.g. Roboflow, Label Studio, CVAT).
2. Convert to YOLO and write into the dataset:

```bash
cd /Users/shailja/clawd/object_detection_working/training

# Train set
python3 coco_to_yolo.py path/to/train_annotations.json train

# Val set
python3 coco_to_yolo.py path/to/val_annotations.json val
```

Class names are read from **dataset/dataset.yaml**. To override:

```bash
python3 coco_to_yolo.py annotations.json train --classes person bottle book
```

Then run **Step 6** (check + train) as above.
