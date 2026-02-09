# Object Detection Training – Work Done So Far

Quick refresh of what’s in place and how to use it.

---

## 1. What You Have

- **RTSP stream viewer** in `object_detection_working/` (Flask on port 5001) that:
  - Takes an RTSP URL and shows the stream in the browser
  - Can overlay **YOLO** detections on the stream
  - Uses your **custom trained model** (not the default COCO model)

- **Custom YOLO model** trained on your own classes:
  - Classes in dataset: **person**, **bottle**, **book** (3 classes)
  - Best weights: `training/runs/detect/runs/detect/custom_yolo5/weights/best.pt`
  - Server is already configured to load this file

- **Training pipeline** under `object_detection_working/training/`:
  - Data collection scripts
  - Dataset split (train / val / test)
  - Annotation helpers and docs
  - Training script and run outputs

---

## 2. Data Collection

- **Issue:** `collect_via_server.py` was failing (connection timeout / “Operation not permitted”) because the Flask server’s ffmpeg couldn’t reach the RTSP stream (macOS permissions).
- **What worked:** Collecting frames **directly** from the machine (e.g. in Terminal):
  - `collect_data.py` (ffmpeg) or
  - `collect_simple.sh` or
  - Manual ffmpeg command from `COLLECT_DATA_GUIDE.md`
- Frames were saved under `dataset/images/`, then split into train/val/test.

---

## 3. Labeling

- **Issue:** LabelImg crashed on Python 3.13 (Qt `drawLine` / float vs int).
- **Alternatives used/suggested:**
  - **makesense.ai** (web) – upload images, annotate, export YOLO format.
  - **Roboflow** (web) – similar workflow, YOLO export.
  - Helper script `quick_label_helper.py` to zip images for upload and organize downloaded labels into `dataset/train/labels` and `dataset/val/labels`.
- Labels were brought into the correct folder structure; some empty `.txt` files were removed later.

---

## 4. Dataset Cleanup

- **Issue:** Training warned: “Labels are missing or empty in …/labels.cache”.
- **Cause:** Some label files were empty; cache was out of date.
- **Done:**
  - Removed empty `.txt` files in `dataset/train/labels` and `dataset/val/labels`.
  - Deleted `labels.cache` in train and val so YOLO could rebuild it.
- After that, training ran without that warning.

---

## 5. Training

- **Script:** `train_custom_model.py` (from `object_detection_working/training/`).
- **Config (in script / dataset):**
  - Model: YOLOv8n (nano)
  - Epochs: 100 (or as set in script)
  - Dataset: `dataset/dataset.yaml` with classes **person**, **bottle**, **book**.
- **Output:** Multiple runs under `training/runs/detect/runs/detect/` (e.g. `custom_yolo`, `custom_yolo5`). The one in use is **custom_yolo5** (best.pt).

---

## 6. Server and Custom Model

- **File:** `object_detection_working/server_yolo.py`.
- **Change made:** Load custom weights instead of `yolov8n.pt`:
  - `YOLO('training/runs/detect/runs/detect/custom_yolo5/weights/best.pt')`
  - Path is relative to `object_detection_working/` (where `server_yolo.py` lives).
- **Earlier bug:** Model path once pointed to a **directory** (`.../weights`) instead of a **file** (`.../weights/best.pt`), causing “model is not a supported format”. That’s fixed.

---

## 7. How to Run It Now

```bash
cd /Users/shailja/clawd/object_detection_working
python3 server_yolo.py
```

- Open: **http://localhost:5001**
- Add your RTSP URL (e.g. `rtsp://kush.sood:admin@123@192.168.29.221/stream1`), enable YOLO, start stream.
- Stream works; if detections are missing or weak, likely causes: confidence threshold, class/label mismatch, or need for more/better training data (see “Detection not showing objects” notes in the repo).

---

## 8. Handy Paths

| What | Where |
|------|--------|
| Viewer + server | `object_detection_working/server_yolo.py` |
| Custom weights in use | `object_detection_working/training/runs/detect/runs/detect/custom_yolo5/weights/best.pt` |
| Dataset (images + labels) | `object_detection_working/training/dataset/` |
| Dataset config | `object_detection_working/training/dataset/dataset.yaml` |
| Training script | `object_detection_working/training/train_custom_model.py` |
| Collection scripts | `object_detection_working/training/collect_*.py`, `collect_simple.sh` |
| Labeling helper | `object_detection_working/training/quick_label_helper.py`, `use_makesense.md` |

---

## 9. If You Want to Improve Detection Later

- Lower confidence in the UI/API (e.g. 0.1) to see if boxes appear.
- Add more diverse labeled images and re-train.
- Ensure annotation class names match `dataset.yaml` exactly (person, bottle, book).
- Check `training/runs/detect/runs/detect/custom_yolo5/results.png` for training/validation curves.

That’s the full refresh of work done so far.
