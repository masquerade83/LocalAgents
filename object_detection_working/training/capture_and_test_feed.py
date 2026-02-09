#!/usr/bin/env python3
"""
Capture 2–3 minutes of RTSP feed into test/captured_frames/, then run inference
with the custom YOLO model and print/save a per-class summary to validate the model.

Usage (from object_detection_working/training/):
  python3 capture_and_test_feed.py [RTSP_URL]

  RTSP_URL optional; default from env RTSP_URL or a built-in default.
  Example: python3 capture_and_test_feed.py "rtsp://user:pass@192.168.1.100/stream1"
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
import cv2

# Paths relative to this script's directory (training/)
SCRIPT_DIR = Path(__file__).resolve().parent
TEST_DIR = SCRIPT_DIR / "test"
CAPTURED_DIR = TEST_DIR / "captured_frames"
ANNOTATED_DIR = TEST_DIR / "annotated"
WEIGHTS = SCRIPT_DIR / "runs" / "detect" / "runs" / "detect" / "custom_yolo10" / "weights" / "best.pt"

# Capture settings
CAPTURE_DURATION_SEC = 150   # 2.5 minutes
FRAME_RATE = 1               # 1 frame per second → ~150 frames
CONF = 0.05                  # Same as server low-confidence run
MAX_ANNOTATED = 5            # Save this many annotated samples


def get_rtsp_url():
    if len(sys.argv) > 1:
        return sys.argv[1].strip()
    return os.environ.get("RTSP_URL", "rtsp://kush.sood:admin%40123@192.168.29.221/stream1")


def capture_feed(rtsp_url: str) -> bool:
    """Capture CAPTURE_DURATION_SEC of feed at FRAME_RATE fps into CAPTURED_DIR."""
    CAPTURED_DIR.mkdir(parents=True, exist_ok=True)
    num_frames = CAPTURE_DURATION_SEC * FRAME_RATE  # e.g. 150

    print("=" * 60)
    print("Step 1: Capture RTSP feed")
    print("=" * 60)
    print(f"RTSP URL:      {rtsp_url}")
    print(f"Duration:      {CAPTURE_DURATION_SEC} s ({CAPTURE_DURATION_SEC/60:.1f} min)")
    print(f"Frame rate:    {FRAME_RATE} fps → ~{num_frames} frames")
    print(f"Output dir:    {CAPTURED_DIR}")
    print("=" * 60)

    cmd = [
        "ffmpeg",
        "-y",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-vf", f"fps={FRAME_RATE},scale=1280:720",
        "-t", str(CAPTURE_DURATION_SEC),
        "-f", "image2",
        "-q:v", "2",
        str(CAPTURED_DIR / "frame_%06d.jpg"),
    ]

    try:
        print("\nCapturing... (this will take about {:.0f} seconds)\n".format(CAPTURE_DURATION_SEC))
        start = time.time()
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        stdout, stderr = proc.communicate()
        elapsed = time.time() - start

        files = list(CAPTURED_DIR.glob("*.jpg"))
        count = len(files)
        if proc.returncode != 0 and count == 0:
            print("❌ Capture failed. ffmpeg stderr (last 500 chars):")
            print((stderr or "")[-500:])
            return False
        print(f"✅ Captured {count} frames in {elapsed:.1f}s → {CAPTURED_DIR}")
        return count > 0
    except FileNotFoundError:
        print("❌ ffmpeg not found. Install with: brew install ffmpeg")
        return False
    except Exception as e:
        print(f"❌ Capture error: {e}")
        return False


def run_inference() -> bool:
    """Run YOLO on all images in CAPTURED_DIR; print and save summary; optionally save annotated images."""
    if not WEIGHTS.is_file():
        print(f"❌ Weights not found: {WEIGHTS}")
        return False

    try:
        from ultralytics import YOLO
    except ImportError:
        print("❌ ultralytics not installed. Run: pip install ultralytics")
        return False

    images = sorted(CAPTURED_DIR.glob("*.jpg"))
    if not images:
        print(f"❌ No images in {CAPTURED_DIR}. Run capture first.")
        return False

    print("\n" + "=" * 60)
    print("Step 2: Run inference on captured frames")
    print("=" * 60)
    print(f"Model:   {WEIGHTS}")
    print(f"Images:  {len(images)}")
    print(f"Conf:    {CONF}")
    print("=" * 60)

    model = YOLO(str(WEIGHTS))
    class_names = list(model.names.values())
    total_counts = {name: 0 for name in class_names}
    per_image = []
    annotated_saved = 0

    ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

    for i, img_path in enumerate(images):
        results = model(str(img_path), conf=CONF, imgsz=640, verbose=False)
        r = results[0]
        counts = {name: 0 for name in class_names}
        if r.boxes is not None and len(r.boxes):
            cls_ids = r.boxes.cls.cpu().numpy().astype(int)
            for cid in cls_ids:
                name = model.names[cid]
                counts[name] = counts.get(name, 0) + 1
                total_counts[name] = total_counts.get(name, 0) + 1
        per_image.append((img_path.name, counts))

        # Save a few annotated frames
        if annotated_saved < MAX_ANNOTATED and r.boxes is not None and len(r.boxes):
            ann = r.plot()
            out_path = ANNOTATED_DIR / img_path.name
            cv2.imwrite(str(out_path), ann)
            annotated_saved += 1

        if (i + 1) % 30 == 0 or i == 0:
            print(f"  Processed {i + 1}/{len(images)} ...")

    # Summary
    print("\n--- Per-class detection totals (all captured frames) ---")
    for name in class_names:
        print(f"  {name}: {total_counts[name]}")
    total_det = sum(total_counts.values())
    frames_with_det = sum(1 for _, c in per_image if sum(c.values()) > 0)
    print(f"\n  Total detections: {total_det}")
    print(f"  Frames with ≥1 detection: {frames_with_det}/{len(images)}")

    # Save summary to file
    summary_path = TEST_DIR / "inference_summary.txt"
    with open(summary_path, "w") as f:
        f.write(f"Inference on captured feed — {datetime.now().isoformat()}\n")
        f.write(f"Frames: {len(images)}  Conf: {CONF}  Weights: {WEIGHTS}\n\n")
        f.write("Per-class totals:\n")
        for name in class_names:
            f.write(f"  {name}: {total_counts[name]}\n")
        f.write(f"\nTotal detections: {total_det}\n")
        f.write(f"Frames with ≥1 detection: {frames_with_det}/{len(images)}\n")
    print(f"\n✅ Summary saved to {summary_path}")
    if annotated_saved:
        print(f"✅ Annotated samples saved to {ANNOTATED_DIR} ({annotated_saved} images)")
    print("\nModel validation: if you see multiple classes above, the model is working on the live feed.")
    return True


def main():
    rtsp_url = get_rtsp_url()
    print(f"Using RTSP URL: {rtsp_url}\n")

    if not capture_feed(rtsp_url):
        sys.exit(1)
    if not run_inference():
        sys.exit(1)
    print("\n✅ Capture + inference test finished successfully.")


if __name__ == "__main__":
    main()
