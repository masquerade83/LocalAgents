# Progress checkpoint & milestones

**Checkpoint date:** January 2026  
**Scope:** RTSP Stream Viewer + YOLO + Analytics + Alerts (object_detection_working)

---

## Project summary

- **Viewer:** Browser-based RTSP stream with optional YOLO object detection (custom 10-class or COCO).
- **Analytics:** Background capture from RTSP → YOLO at interval → SQLite (detection events) → configurable triggers.
- **Alerts:** Triggers fire on rules (e.g. class detected, count above threshold); send via Email (SMTP), SMS (Twilio), and/or **WhatsApp** (Twilio).
- **WhatsApp extras:** Configurable alert message template in dashboard; optional **attach current frame image** to WhatsApp (requires public URL, e.g. ngrok).

---

## Milestones completed

| # | Milestone | Status |
|---|-----------|--------|
| 1 | RTSP viewer with MJPEG + YOLO (Flask, ffmpeg, Ultralytics) | ✅ |
| 2 | Custom YOLO model (10 classes) integrated; live stream shows “Model: custom 10-class” | ✅ |
| 3 | Analytics DB (SQLite): detection events, triggers, alerts_sent | ✅ |
| 4 | Analytics capture pipeline: RTSP → ffmpeg → YOLO → insert detections → evaluate triggers | ✅ |
| 5 | Trigger rules: class_detected, count_above; cooldown per trigger | ✅ |
| 6 | Notifications: Email (SMTP), SMS (Twilio), WhatsApp (Twilio API) | ✅ |
| 7 | Dashboard: reports (by class/hour/day), triggers CRUD, capture start/stop | ✅ |
| 8 | WhatsApp configured in .env; test message to configured number working | ✅ |
| 9 | Alert message config in dashboard: template ({trigger_name}, {message}), include frame with WhatsApp, public base URL | ✅ |
| 10 | Attach frame to WhatsApp on trigger fire (save frame, Twilio fetches from public URL) | ✅ |
| 11 | Tunnel setup (ngrok) for public URL; TUNNEL.md + run_tunnel.sh | ✅ |
| 12 | Alert delivery fix: .env loaded in analytics capture thread; cooldown only when previous send exists; trigger-status API + “Send test alert” | ✅ |

---

## Current capabilities

- **Local viewer:** Open `http://localhost:5001`, enter RTSP URL, Connect → live stream with YOLO.
- **Dashboard:** `http://localhost:5001/dashboard` — reports, triggers, alert message template, start/stop analytics capture.
- **Triggers:** Add rules (e.g. “person” detected, or count above N), enable Email/SMS/WhatsApp; alerts respect cooldown.
- **WhatsApp:** Alerts (and optional frame image) delivered when trigger fires; “Send test WhatsApp” and “Send test alert (template)” for verification.
- **Trigger status:** “Check trigger status” shows capture_running, whatsapp_configured, per-trigger last_alert and config.

---

## Deferred / known limitations

- **Browser over tunnel:** Live RTSP viewer can show a black screen when opened via the public ngrok URL; WhatsApp alert images still work. Use viewer on localhost for live feed; see TUNNEL.md and app.js fetch/MJPEG path for future debug.
- **count_above:** Uses current-frame count only (no rolling time-window in DB); cooldown avoids spam.

---

## How to run (checkpoint)

1. **Env:** Copy/configure `.env` (see `analytics/env.example`). Required for WhatsApp: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `ANALYTICS_ALERT_WHATSAPP_TO`.
2. **Server:** `python3 server_yolo.py` (or `./start_yolo.sh`) → http://localhost:5001.
3. **Viewer:** Open `/`, enter RTSP URL, Connect.
4. **Analytics:** Open `/dashboard`, set RTSP URL, Start analytics. Add triggers (e.g. class_detected “person”), enable WhatsApp, set cooldown.
5. **Alert template / frame:** In dashboard, set “Alert message & options” (template, “Attach frame”, public base URL if using images) and Save.
6. **Tunnel (for WhatsApp images):** Run `./run_tunnel.sh` (or `ngrok http 5001`), put HTTPS URL in “Public base URL”, Save.

---

## Key files (reference)

| Area | Files |
|------|--------|
| Server & viewer | `server_yolo.py`, `index.html`, `app.js`, `styles.css` |
| Analytics | `analytics/capture.py`, `analytics/triggers.py`, `analytics/notify.py`, `analytics/db.py`, `analytics/config.py`, `analytics/alert_config.py` |
| Config & tunnel | `.env`, `analytics/alert_config.json`, `TUNNEL.md`, `run_tunnel.sh` |
| Docs | `README.md`, `analytics/README.md`, `TECH_STACK.md` |

---

*This file is the checkpoint and milestone list for the object_detection_working stack. Update when completing new milestones or changing scope.*
