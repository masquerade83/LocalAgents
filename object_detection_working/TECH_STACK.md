# Tech Stack & Backend Details

**Project:** RTSP stream viewer with custom YOLO object detection and analytics.

---

## Overview

- **Backend:** Single Flask app (Python 3) serving live RTSP→browser streams, YOLO inference, and an analytics layer (storage, reports, triggers, email/SMS alerts).
- **ML:** Custom YOLOv8 (Ultralytics) trained on 10 classes; inference at 640px; only custom weights are loaded (no COCO fallback).
- **Streaming:** FFmpeg for RTSP decode; MJPEG over HTTP for both live view and analytics capture (frame-boundary safe).

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3 (3.11+) |
| **Web framework** | Flask 3.x |
| **CORS** | flask-cors |
| **ML / object detection** | Ultralytics (YOLOv8), custom 10-class weights |
| **Vision / video** | OpenCV (cv2), NumPy |
| **Streaming** | FFmpeg (subprocess), MJPEG over HTTP |
| **Database** | SQLite (analytics only; file: `analytics/analytics.db`) |
| **Email** | smtplib (stdlib) |
| **SMS (optional)** | Twilio (`twilio` package) |
| **Frontend** | Vanilla JS, HTML5 (video/img), Chart.js (dashboard) |

### Core dependencies (`requirements_yolo.txt`)

```
flask==3.0.0
flask-cors==4.0.0
ultralytics==8.3.0
opencv-python==4.9.0.80
numpy==1.26.4
```

### Optional

- **SMS alerts:** `twilio>=8.0.0` (see `requirements_analytics.txt`).

---

## Backend Structure

```
object_detection_working/
├── server_yolo.py          # Main app: streams, YOLO, analytics API
├── index.html              # Stream viewer UI
├── app.js                  # Viewer logic (connect, MJPEG, confidence)
├── dashboard.html          # Analytics dashboard (reports, triggers)
├── analytics/
│   ├── __init__.py
│   ├── db.py               # SQLite schema, detection/trigger/alert CRUD
│   ├── config.py           # Env-based config (SMTP, Twilio)
│   ├── capture.py          # Background RTSP→YOLO→DB + trigger check
│   ├── triggers.py         # Rule evaluation (class_detected, count_above) + cooldown
│   ├── notify.py           # Email (SMTP) and SMS (Twilio) sending
│   ├── analytics.db        # SQLite DB (created at first run)
│   └── README.md           # Analytics env and usage
├── training/               # Dataset, training scripts, weights
│   ├── train_custom_model.py
│   ├── dataset/
│   ├── runs/detect/.../custom_yolo10/weights/best.pt
│   ├── capture_and_test_feed.py
│   └── ...
├── requirements_yolo.txt
└── requirements_analytics.txt   # Optional: twilio
```

---

## API Reference

**Base URL:** `http://localhost:5001` (or your host).

### Pages

| Route | Description |
|-------|-------------|
| `GET /` | Stream viewer (RTSP URL, YOLO toggle, confidence). |
| `GET /debug` | Debug stream page. |
| `GET /dashboard` | Analytics dashboard (reports, triggers, capture control). |

### Stream & YOLO

| Method | Route | Description |
|--------|--------|-------------|
| `POST` | `/api/stream/start` | Start stream. Body: `{ "url": "rtsp://...", "yolo": true, "confidence": 0.05 }`. Returns `stream_url` (MJPEG with query params). |
| `POST` | `/api/stream/stop` | Stop all streams. |
| `GET` | `/api/stream/mjpeg` | MJPEG stream. Query: `url`, `yolo`, `confidence`, `t` (cache-bust). |
| `GET` | `/api/stream/status` | Active streams and YOLO availability. |
| `GET` | `/api/yolo/model-info` | Loaded model path and class names (10-class check). |

### Analytics

| Method | Route | Description |
|--------|--------|-------------|
| `GET` | `/api/analytics/status` | Capture running or not + `stream_id`. |
| `POST` | `/api/analytics/start` | Start analytics capture. Body: `{ "rtsp_url", "interval_sec?", "confidence?" }`. |
| `POST` | `/api/analytics/stop` | Stop analytics capture. |
| `GET` | `/api/analytics/detections` | Query: `from_ts`, `to_ts`, `stream_id?`, `class_name?`, `limit?`. Returns list of detection events. |
| `GET` | `/api/analytics/summary` | Query: `from_ts`, `to_ts`, `group_by` (class \| hour \| day), `stream_id?`. Returns aggregated counts. |
| `GET` | `/api/analytics/triggers` | List triggers. Query: `enabled` (default 1). |
| `POST` | `/api/analytics/triggers` | Create trigger. Body: `name`, `rule_type`, `rule_config`, `stream_id?`, `cooldown_sec?`, `notify_email?`, `notify_sms?`. |
| `DELETE` | `/api/analytics/triggers/<id>` | Delete trigger. |
| `POST` | `/api/analytics/triggers/<id>/toggle` | Enable/disable. Body: `{ "enabled": true \| false }`. |
| `GET` | `/api/analytics/notify-config` | Whether email/SMS env is configured. |

### Health

| Method | Route | Description |
|--------|--------|-------------|
| `GET` | `/api/health` | ffmpeg and YOLO availability. |

---

## Data Storage (SQLite)

**File:** `analytics/analytics.db`

| Table | Purpose |
|-------|--------|
| `detection_events` | One row per detection: `stream_id`, `rtsp_url`, `class_name`, `confidence`, `ts` (Unix). Indexed on `ts`, `stream_id`, `class_name`. |
| `triggers` | Trigger rules: `name`, `stream_id`, `rule_type`, `rule_config` (JSON), `cooldown_sec`, `notify_email`, `notify_sms`, `enabled`. |
| `alerts_sent` | Alert history: `trigger_id`, `message`, `channel`, `sent_at` (for cooldown and audit). |

---

## Model & Detection

- **Model:** YOLOv8n (nano), fine-tuned; 10 classes: `ac`, `artwork`, `book`, `bottle`, `box`, `cup`, `curtain`, `fan`, `lamp`, `person`.
- **Weights path:** `training/runs/detect/runs/detect/custom_yolo10/weights/best.pt` (resolved relative to server script).
- **Inference:** 640px, configurable confidence (default 0.05 for live view; analytics capture default 0.25).
- **Policy:** Server loads only the custom 10-class weights; if the file is missing or not 10-class, no model is loaded and streams are video-only.

---

## Notifications (env-based)

- **Email:** `ANALYTICS_SMTP_HOST`, `ANALYTICS_SMTP_PORT`, `ANALYTICS_SMTP_USER`, `ANALYTICS_SMTP_PASS`, `ANALYTICS_ALERT_EMAIL_TO` (comma-separated). Optional: `ANALYTICS_ALERT_EMAIL_FROM`.
- **SMS:** `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `ANALYTICS_ALERT_PHONE_TO` (E.164, comma-separated). Requires `twilio` package.

---

## Runtime

- **Start:** From `object_detection_working`: `python3 server_yolo.py`.
- **Port:** 5001.
- **Threading:** Flask with `threaded=True`; analytics capture runs in a separate daemon thread.
- **Requirements:** FFmpeg on PATH; Python deps from `requirements_yolo.txt` (and optionally `requirements_analytics.txt` for SMS).

---

*Generated from the current codebase. Update this doc when adding routes or changing stack.*
