# Capture training data

Frames are collected from your RTSP stream using **ffmpeg**. Run these commands **in your Mac Terminal** (not from Cursor), so ffmpeg has network permission.

---

## Quick start

```bash
cd /Users/shailja/clawd/object_detection_working/training
./collect_simple.sh
```

- Captures **100 frames** (1 every 2 seconds) into `dataset/images`.
- If you already have frames there, this **overwrites** the first 100 files.

---

## Add more frames (no overwrite)

To add another batch without touching existing images:

```bash
cd /Users/shailja/clawd/object_detection_working/training
chmod +x collect_more.sh
./collect_more.sh
```

- Adds 100 more frames with continued numbering (e.g. 105–204 if you had 104).
- Merges into `dataset/images`. Then run `python3 split_dataset.py` again.

---

## Options

| Script               | Effect |
|----------------------|--------|
| `./collect_simple.sh` | 100 frames into `dataset/images` (can overwrite) |
| `./collect_more.sh`   | 100 more frames appended (no overwrite) |
| `python3 collect_data.py` | Same as above; uses `collect_data.py` settings (e.g. MAX_FRAMES=1000) |

To change count or interval, edit the variables at the top of `collect_simple.sh` / `collect_more.sh` or `collect_data.py` (e.g. `MAX_FRAMES`, `FRAME_INTERVAL`).

---

## After capture

1. Split: `python3 split_dataset.py`
2. Annotate: use makesense.ai or Roboflow (see `use_makesense.md`), put `.txt` labels in `dataset/train/labels` and `dataset/val/labels`.
3. Train: `python3 train_custom_model.py`
