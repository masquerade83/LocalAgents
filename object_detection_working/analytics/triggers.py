"""
Evaluate trigger rules against current/latest detections and send alerts with cooldown.
Rule types:
  - class_detected: fire when class_name is detected (any confidence >= min_conf)
  - count_above: fire when count of class_name in last window_sec >= count
"""
import json
import os
import time
from . import db
from . import notify
from . import alert_config


def _parse_config(rule_config_str):
    try:
        return json.loads(rule_config_str)
    except Exception:
        return {}


def check_triggers(stream_id: str, detections: list, frame=None):
    """
    detections: list of {"class_name": str, "confidence": float}
    frame: optional numpy/cv2 image (BGR) to save and attach to WhatsApp when include_frame_with_whatsapp is on.
    For each enabled trigger, evaluate rule; if fired and cooldown passed, send alert.
    """
    now = time.time()
    triggers = db.get_triggers(enabled_only=True)
    if not triggers:
        return
    alert_cfg = alert_config.get_config()
    message_template = alert_cfg.get("message_template", "{trigger_name}: {message}")
    include_frame = alert_cfg.get("include_frame_with_whatsapp", False)
    public_base_url = (alert_cfg.get("public_base_url") or "").strip().rstrip("/")

    for t in triggers:
        if t["stream_id"] and t["stream_id"] != stream_id:
            continue
        cfg = _parse_config(t["rule_config"] or "{}")
        rule_type = t["rule_type"]
        fired = False
        message = ""

        if rule_type == "class_detected":
            want_class = cfg.get("class_name", "")
            min_conf = float(cfg.get("min_confidence", 0))
            for d in detections:
                if d.get("class_name") == want_class and d.get("confidence", 0) >= min_conf:
                    fired = True
                    message = f"Class '{want_class}' detected (conf={d.get('confidence', 0):.2f})"
                    break

        elif rule_type == "count_above":
            want_class = cfg.get("class_name", "")
            threshold = int(cfg.get("count", 1))
            window_sec = int(cfg.get("window_sec", 60))
            # We only have current frame counts here; for true window we'd need DB. Use current frame count as proxy.
            count = sum(1 for d in detections if d.get("class_name") == want_class)
            if count >= threshold:
                fired = True
                message = f"Class '{want_class}' count >= {threshold} (current frame: {count})"

        if not fired:
            continue

        # Cooldown
        last = db.last_alert_time(t["id"])
        if last and now - last < t["cooldown_sec"]:
            continue

        # Build body from template
        body = message_template.replace("{trigger_name}", t["name"]).replace("{message}", message)

        # Optional: save frame and attach to WhatsApp
        media_url = None
        via_email = bool(t["notify_email"])
        via_sms = bool(t.get("notify_sms", 0))
        via_whatsapp = bool(t.get("notify_whatsapp", 0))
        if via_whatsapp and include_frame and frame is not None and public_base_url:
            try:
                import cv2
                alert_frames_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alert_frames")
                os.makedirs(alert_frames_dir, exist_ok=True)
                path = os.path.join(alert_frames_dir, "latest.jpg")
                cv2.imwrite(path, frame)
                media_url = [f"{public_base_url}/api/analytics/alert-frame"]
            except Exception as e:
                print(f"[Analytics] Failed to save alert frame: {e}")

        if via_email or via_sms or via_whatsapp:
            channel = ",".join(c for c in ["email", "sms", "whatsapp"] if (c == "email" and via_email) or (c == "sms" and via_sms) or (c == "whatsapp" and via_whatsapp))
            print(f"[Analytics] Trigger '{t['name']}' fired → sending via {channel}")
            notify.send_alert(t["name"], message, via_email, via_sms, via_whatsapp, body=body, media_url=media_url)
            db.record_alert_sent(t["id"], message, channel)
