# Notion update: Object Detection Training – Project Refresh

**Page:** [Object Detection Training – Project Refresh](https://www.notion.so/3009eda1d5b381b3bb50caf8ea06e74f)

---

## Paste this as Section 10 (at the end of the page)

---

## 10. Milestone 1 complete – Live feed with custom 10-class model (Feb 2026)

- **Dataset:** 10 classes: **ac, artwork, book, bottle, box, cup, curtain, fan, lamp, person**. Train: 154 images, 7,781 annotations; Val: 38 images, 1,848 annotations.

- **Weights in use:** `training/runs/detect/runs/detect/custom_yolo10/weights/best.pt`. Server uses script-relative path so it works regardless of cwd.

- **Server behaviour:** Loads **only** the custom 10-class weights; validates the class list and **refuses** to use COCO. If you see "potted plant" or "couch" on the video, you're on an old server – kill it and run the one from `object_detection_working`.

- **On-screen check:** When the custom model is active, green text at bottom of video: **"Model: custom 10-class"**. No COCO labels.

- **Live stream:** Uses **MJPEG** from ffmpeg (frame-boundary safe, no raw buffer alignment issues). Stream URL includes confidence (default 0.05) and a timestamp so each Connect gets a fresh stream. Disconnect and reconnect after a server restart.

- **Validation:**  
  - `training/capture_and_test_feed.py` – capture 2–3 min of RTSP feed into `training/test/captured_frames/`, then run inference and save summary to `training/test/inference_summary.txt`.  
  - `training/run_inference_test.py` – run model on val images to verify per-class predictions.

- **API:** GET `/api/yolo/model-info` returns loaded model path and class names. Run server from `object_detection_working`: `python3 server_yolo.py`.

---

## Find & replace in the rest of the Notion page

| Find | Replace with |
|------|------------------|
| Classes in dataset: **person**, **bottle**, **book** (3 classes) | Classes in dataset: **ac, artwork, book, bottle, box, cup, curtain, fan, lamp, person** (10 classes) |
| `custom_yolo5/weights/best.pt` | `custom_yolo10/weights/best.pt` |
| Custom weights in use: `...custom_yolo5/...` | Custom weights in use: `object_detection_working/training/runs/detect/runs/detect/custom_yolo10/weights/best.pt` |
| dataset.yaml with classes **person**, **bottle**, **book** | dataset.yaml with 10 classes (ac, artwork, book, bottle, box, cup, curtain, fan, lamp, person) |
| The one in use is **custom_yolo5** | The one in use is **custom_yolo10** |
| Ensure annotation class names match `dataset.yaml` exactly (person, bottle, book) | Ensure annotation class names match `dataset.yaml` (10 classes: ac, artwork, book, bottle, box, cup, curtain, fan, lamp, person) |
| custom_yolo5/results.png | custom_yolo10/results.png |

---

That's the full update for the same Notion file.
