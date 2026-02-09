#!/usr/bin/env python3
"""
RTSP Stream Viewer with YOLO Object Detection
Converts RTSP streams to browser-compatible formats with real-time object detection
"""
from flask import Flask, Response, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
import subprocess
import threading
import os
import signal
import time
import cv2
import numpy as np
from ultralytics import YOLO
import io

# Optional: load .env for ANALYTICS_*, TWILIO_* (pip install python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Store active stream processes
active_streams = {}
stream_lock = threading.Lock()

# Global YOLO model (loaded once)
yolo_model = None
model_lock = threading.Lock()

# Expected custom 10-class names (must match training). If loaded model doesn't match, we refuse to use it.
CUSTOM_CLASSES = ['ac', 'artwork', 'book', 'bottle', 'box', 'cup', 'curtain', 'fan', 'lamp', 'person']

def _model_weights_path():
    """Path to custom weights (script-relative so it works regardless of cwd)."""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'training', 'runs', 'detect', 'runs', 'detect', 'custom_yolo10', 'weights', 'best.pt')

def _is_custom_model(model):
    """True if this is our 10-class custom model, not COCO."""
    if model is None or not hasattr(model, 'names'):
        return False
    names = list(model.names.values()) if isinstance(model.names, dict) else model.names
    if len(names) != 10:
        return False
    return set(names) == set(CUSTOM_CLASSES)

def load_yolo_model():
    """Load YOLO model – only our custom 10-class weights. Never use COCO."""
    global yolo_model
    with model_lock:
        if yolo_model is None:
            try:
                weights_path = _model_weights_path()
                print(f"Loading YOLO model from: {weights_path}")
                if not os.path.isfile(weights_path):
                    print(f"❌ Weights file not found: {weights_path}")
                    print("   Live feed will show stream WITHOUT detection until custom weights exist.")
                    return None
                yolo_model = YOLO(weights_path)
                if not _is_custom_model(yolo_model):
                    print(f"❌ Loaded model is not the custom 10-class model (got: {list(yolo_model.names.values())})")
                    print("   Refusing to use it. Fix the weights path or retrain.")
                    yolo_model = None
                    return None
                print("✅ Custom 10-class model loaded successfully")
                print(f"   Classes: {list(yolo_model.names.values())}")
            except Exception as e:
                print(f"❌ Failed to load YOLO model: {e}")
                yolo_model = None
                return None
    return yolo_model

def _read_one_jpeg(stream):
    """Read one complete JPEG from stream (SOI ... EOI). Returns bytes or None."""
    SOI = b'\xff\xd8'
    EOI = b'\xff\xd9'
    buf = b''
    while True:
        chunk = stream.read(4096)
        if not chunk:
            return None
        buf += chunk
        start = buf.find(SOI)
        if start == -1:
            buf = buf[-1:]  # keep one byte in case SOI is split
            continue
        end = buf.find(EOI, start)
        if end == -1:
            buf = buf[start:]
            continue
        end += 2
        return buf[start:end]

def create_yolo_stream(rtsp_url, confidence=0.05):
    """
    Create annotated MJPEG stream from RTSP using ffmpeg MJPEG + YOLO.
    Uses MJPEG from ffmpeg (frame-boundary safe) so each frame is one JPEG - no alignment issues.
    """
    model = load_yolo_model()
    if model is None:
        return create_mjpeg_stream_fallback(rtsp_url)

    # ffmpeg outputs MJPEG (each frame is a complete JPEG) - no raw buffer alignment issues
    cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,
        '-vf', 'fps=10,scale=1280:720',
        '-q:v', '3',
        '-f', 'mjpeg',
        '-'
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )

        def generate():
            frame_count = 0
            try:
                while True:
                    jpeg_bytes = _read_one_jpeg(process.stdout)
                    if jpeg_bytes is None:
                        break
                    frame = cv2.imdecode(np.frombuffer(jpeg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        continue
                    if frame_count == 0:
                        print(f"[YOLO] Stream frame size: {frame.shape[1]}x{frame.shape[0]} (MJPEG), conf={confidence}")

                    results = model(frame, conf=confidence, imgsz=640, verbose=False)
                    r = results[0]
                    if frame_count > 0 and frame_count % 60 == 0:
                        if r.boxes is not None and len(r.boxes):
                            cls_ids = r.boxes.cls.cpu().numpy().astype(int)
                            counts = {}
                            for cid in cls_ids:
                                name = model.names.get(cid, f"cls_{cid}")
                                counts[name] = counts.get(name, 0) + 1
                            print(f"[YOLO] Frame {frame_count} detections: {dict(sorted(counts.items()))}")
                        else:
                            print(f"[YOLO] Frame {frame_count} detections: (none)")

                    annotated = r.plot()
                    # So you can verify: custom model shows this label; COCO does not
                    cv2.putText(
                        annotated, "Model: custom 10-class",
                        (10, annotated.shape[0] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
                    )
                    _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    frame_count += 1
            except Exception as e:
                print(f"Stream error: {e}")
            finally:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception:
                    process.kill()

        return generate()
    except Exception as e:
        print(f"Failed to start ffmpeg for YOLO stream: {e}")
        return create_mjpeg_stream_fallback(rtsp_url)

def create_mjpeg_stream_fallback(rtsp_url):
    """Fallback to regular MJPEG stream without YOLO"""
    cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,
        '-vf', 'fps=10,scale=1280:-1',
        '-q:v', '5',
        '-f', 'mjpeg',
        '-'
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )
        
        def generate():
            try:
                while True:
                    chunk = process.stdout.read(1024)
                    if not chunk:
                        break
                    
                    frame = chunk
                    while True:
                        chunk = process.stdout.read(1024)
                        if not chunk:
                            break
                        frame += chunk
                        if frame[-2:] == b'\xff\xd9':
                            break
                    
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                print(f"Stream error: {e}")
            finally:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    process.kill()
        
        return generate()
    except Exception as e:
        print(f"Failed to start ffmpeg: {e}")
        return None

@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory('.', 'index.html')

@app.route('/debug')
def debug():
    """Debug page for testing MJPEG stream"""
    return send_from_directory('.', 'debug_stream.html')

def _stream_url_with_params(rtsp_url, use_yolo, confidence):
    import urllib.parse
    enc = urllib.parse.quote(rtsp_url, safe='')
    return f"/api/stream/mjpeg?url={enc}&yolo={str(use_yolo).lower()}&confidence={confidence}&t={int(time.time())}"

@app.route('/api/stream/start', methods=['POST'])
def start_stream():
    """Start an RTSP stream with optional YOLO detection"""
    data = request.json
    rtsp_url = data.get('url')
    use_yolo = data.get('yolo', True)
    confidence = float(data.get('confidence', 0.05))
    
    if not rtsp_url:
        return jsonify({"error": "RTSP URL is required"}), 400
    
    if not rtsp_url.startswith('rtsp://'):
        return jsonify({"error": "Invalid RTSP URL format"}), 400
    
    stream_id = rtsp_url
    stream_url = _stream_url_with_params(rtsp_url, use_yolo, confidence)
    
    with stream_lock:
        if stream_id in active_streams:
            return jsonify({
                "message": "Stream already active",
                "stream_url": stream_url,
                "format": "MJPEG",
                "yolo": use_yolo
            })
        
        active_streams[stream_id] = {
            "url": rtsp_url,
            "yolo": use_yolo,
            "confidence": confidence,
            "started": time.time()
        }
    
    return jsonify({
        "message": "Stream started",
        "stream_url": stream_url,
        "format": "MJPEG",
        "yolo": use_yolo
    })

@app.route('/api/stream/stop', methods=['POST'])
def stop_stream():
    """Stop all active streams"""
    with stream_lock:
        active_streams.clear()
    
    return jsonify({"message": "All streams stopped"})

@app.route('/api/stream/test-frame')
def stream_test_frame():
    """Return a single JPEG frame for testing tunnel/ngrok (no RTSP). Use to verify video path works."""
    buf = np.zeros((100, 100, 3), dtype=np.uint8)
    buf[:, :] = [40, 120, 200]  # blue
    _, jpeg = cv2.imencode('.jpg', buf)
    return Response(
        jpeg.tobytes(),
        mimetype='image/jpeg',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@app.route('/api/stream/mjpeg')
def mjpeg_stream():
    """MJPEG stream endpoint with optional YOLO"""
    stream_url = request.args.get('url')
    use_yolo = request.args.get('yolo', 'true').lower() == 'true'
    confidence = float(request.args.get('confidence', 0.05))
    
    if not stream_url:
        return jsonify({"error": "Stream URL parameter required"}), 400
    
    try:
        import urllib.parse
        rtsp_url = urllib.parse.unquote(stream_url)
    except Exception:
        rtsp_url = stream_url

    print(f"[YOLO] MJPEG request: yolo={use_yolo}, confidence={confidence}")
    
    # Headers to reduce proxy/tunnel buffering so stream reaches the browser
    stream_headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'X-Accel-Buffering': 'no',
    }
    if use_yolo:
        return Response(
            create_yolo_stream(rtsp_url, confidence),
            mimetype='multipart/x-mixed-replace; boundary=frame',
            headers=stream_headers
        )
    else:
        return Response(
            create_mjpeg_stream_fallback(rtsp_url),
            mimetype='multipart/x-mixed-replace; boundary=frame',
            headers=stream_headers
        )

@app.route('/api/yolo/model-info', methods=['GET'])
def yolo_model_info():
    """Return loaded YOLO model path and class names (for verifying server has correct model)."""
    model = load_yolo_model()
    if model is None:
        return jsonify({
            "loaded": False,
            "path": _model_weights_path(),
            "classes": [],
            "num_classes": 0,
            "message": "YOLO model failed to load. Check server logs and that weights file exists."
        })
    # model.names is dict like {0: 'ac', 1: 'artwork', ...}
    classes = [model.names[i] for i in range(len(model.names))]
    return jsonify({
        "loaded": True,
        "path": _model_weights_path(),
        "classes": classes,
        "num_classes": len(classes),
    })

@app.route('/api/stream/status', methods=['GET'])
def stream_status():
    """Get status of active streams"""
    with stream_lock:
        streams = list(active_streams.keys())
    
    yolo_available = yolo_model is not None
    
    return jsonify({
        "active_streams": len(streams),
        "streams": streams,
        "yolo_available": yolo_available
    })

# ---------- Analytics ----------
def _analytics_db():
    from analytics import db
    return db

@app.route('/dashboard')
def dashboard():
    """Analytics dashboard (reports, triggers)."""
    return send_from_directory('.', 'dashboard.html')

@app.route('/api/analytics/status', methods=['GET'])
def analytics_status():
    from analytics.capture import is_capture_running
    running, stream_id = is_capture_running()
    return jsonify({"running": running, "stream_id": stream_id})

@app.route('/api/analytics/start', methods=['POST'])
def analytics_start():
    data = request.json or {}
    rtsp_url = data.get('rtsp_url') or data.get('url')
    if not rtsp_url or not rtsp_url.startswith('rtsp://'):
        return jsonify({"error": "rtsp_url required"}), 400
    model = load_yolo_model()
    if model is None:
        return jsonify({"error": "YOLO model not loaded"}), 503
    from analytics.capture import start_capture
    interval_sec = float(data.get('interval_sec', 1.0))
    confidence = float(data.get('confidence', 0.25))
    ok, msg = start_capture(rtsp_url, model, interval_sec=interval_sec, confidence=confidence)
    if not ok:
        return jsonify({"error": msg}), 400
    return jsonify({"message": msg, "stream_id": rtsp_url})

@app.route('/api/analytics/stop', methods=['POST'])
def analytics_stop():
    from analytics.capture import stop_capture
    ok, msg = stop_capture()
    return jsonify({"message": msg})

@app.route('/api/analytics/detections', methods=['GET'])
def analytics_detections():
    db = _analytics_db()
    stream_id = request.args.get('stream_id')
    class_name = request.args.get('class_name')
    from_ts = request.args.get('from_ts', type=float)
    to_ts = request.args.get('to_ts', type=float)
    limit = request.args.get('limit', 5000, type=int)
    rows = db.get_detections(stream_id=stream_id, class_name=class_name, from_ts=from_ts, to_ts=to_ts, limit=limit)
    for r in rows:
        if 'ts' in r and r['ts'] is not None:
            r['ts'] = float(r['ts'])
    return jsonify({"detections": rows})

@app.route('/api/analytics/summary', methods=['GET'])
def analytics_summary():
    db = _analytics_db()
    from_ts = request.args.get('from_ts', type=float)
    to_ts = request.args.get('to_ts', type=float)
    if from_ts is None or to_ts is None:
        return jsonify({"error": "from_ts and to_ts required (Unix seconds)"}), 400
    stream_id = request.args.get('stream_id')
    group_by = request.args.get('group_by', 'class')
    if group_by not in ('class', 'hour', 'day'):
        group_by = 'class'
    rows = db.get_summary(from_ts, to_ts, stream_id=stream_id, group_by=group_by)
    return jsonify({"summary": rows})

@app.route('/api/analytics/triggers', methods=['GET'])
def analytics_triggers_list():
    db = _analytics_db()
    enabled_only = request.args.get('enabled', '1') == '1'
    triggers = db.get_triggers(enabled_only=enabled_only)
    return jsonify({"triggers": triggers})

@app.route('/api/analytics/triggers', methods=['POST'])
def analytics_triggers_create():
    data = request.json or {}
    name = data.get('name')
    rule_type = data.get('rule_type')
    rule_config = data.get('rule_config')
    if not name or not rule_type:
        return jsonify({"error": "name and rule_type required"}), 400
    if isinstance(rule_config, dict):
        import json
        rule_config = json.dumps(rule_config)
    db = _analytics_db()
    stream_id = data.get('stream_id') or None
    cooldown_sec = int(data.get('cooldown_sec', 300))
    notify_email = bool(data.get('notify_email', False))
    notify_sms = bool(data.get('notify_sms', False))
    notify_whatsapp = bool(data.get('notify_whatsapp', False))
    tid = db.add_trigger(name, stream_id, rule_type, rule_config or "{}", cooldown_sec, notify_email, notify_sms, notify_whatsapp)
    return jsonify({"id": tid, "message": "Trigger created"})

@app.route('/api/analytics/triggers/<int:trigger_id>', methods=['DELETE'])
def analytics_trigger_delete(trigger_id):
    _analytics_db().delete_trigger(trigger_id)
    return jsonify({"message": "Deleted"})

@app.route('/api/analytics/triggers/<int:trigger_id>/toggle', methods=['POST'])
def analytics_trigger_toggle(trigger_id):
    data = request.json or {}
    enabled = data.get('enabled', True)
    _analytics_db().toggle_trigger(trigger_id, enabled)
    return jsonify({"message": "Updated", "enabled": enabled})

@app.route('/api/analytics/notify-config', methods=['GET'])
def analytics_notify_config():
    from analytics import config
    return jsonify({
        "email_configured": config.email_configured(),
        "sms_configured": config.sms_configured(),
        "whatsapp_configured": config.whatsapp_configured(),
    })


@app.route('/api/analytics/trigger-status', methods=['GET'])
def analytics_trigger_status():
    """List triggers with last alert time (for debugging why alerts might not fire)."""
    db = _analytics_db()
    triggers = db.get_triggers(enabled_only=False)
    from analytics import config
    status = []
    for t in triggers:
        last = db.last_alert_time(t["id"])
        status.append({
            "id": t["id"],
            "name": t["name"],
            "enabled": bool(t.get("enabled", 1)),
            "notify_whatsapp": bool(t.get("notify_whatsapp", 0)),
            "stream_id": t.get("stream_id") or "(any)",
            "last_alert_at": last,
            "last_alert_ago": round(time.time() - last, 0) if last else None,
        })
    try:
        from analytics.capture import is_capture_running
        capture_running, _ = is_capture_running()
    except Exception:
        capture_running = False
    return jsonify({
        "triggers": status,
        "whatsapp_configured": config.whatsapp_configured(),
        "capture_running": capture_running,
    })


@app.route('/api/analytics/test-whatsapp', methods=['POST'])
def analytics_test_whatsapp():
    """Send a test WhatsApp message to the configured number(s)."""
    from analytics import config, notify
    if not config.whatsapp_configured():
        return jsonify({"ok": False, "message": "WhatsApp not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, ANALYTICS_ALERT_WHATSAPP_TO in .env"}), 400
    body = "Test message from YOLO Analytics. WhatsApp notifications are working."
    ok = notify.send_whatsapp(body)
    return jsonify({"ok": ok, "message": "Test message sent to " + config.ALERT_WHATSAPP_TO if ok else "Send failed (check server logs)"})


@app.route('/api/analytics/send-test-alert', methods=['POST'])
def analytics_send_test_alert():
    """Send a test alert via WhatsApp using the current alert message template (same path as real triggers)."""
    from analytics import config, notify, alert_config
    if not config.whatsapp_configured():
        return jsonify({"ok": False, "message": "WhatsApp not configured."}), 400
    cfg = alert_config.get_config()
    template = cfg.get("message_template", "{trigger_name}: {message}")
    body = template.replace("{trigger_name}", "Test").replace("{message}", "Manual test alert from dashboard.")
    ok = notify.send_whatsapp(body)
    return jsonify({"ok": ok, "message": "Test alert sent to " + config.ALERT_WHATSAPP_TO if ok else "Send failed (check server logs)"})


@app.route('/api/analytics/test-email', methods=['POST'])
def analytics_test_email():
    """Send a test email to the configured address(es)."""
    from analytics import config, notify
    if not config.email_configured():
        return jsonify({"ok": False, "message": "Email not configured. Set ANALYTICS_SMTP_* and ANALYTICS_ALERT_EMAIL_TO in .env"}), 400
    ok = notify.send_email("[YOLO Analytics] Test", "Test message from YOLO Analytics. Email notifications are working.")
    return jsonify({"ok": ok, "message": "Test email sent to " + config.ALERT_EMAIL_TO if ok else "Send failed (check server logs)"})


@app.route('/api/analytics/alert-config', methods=['GET'])
def analytics_alert_config_get():
    """Get alert message template and options (include_frame_with_whatsapp, public_base_url)."""
    from analytics import alert_config
    return jsonify(alert_config.get_config())


@app.route('/api/analytics/alert-config', methods=['PUT'])
def analytics_alert_config_put():
    """Update alert message template and options."""
    from analytics import alert_config
    data = request.get_json() or {}
    cfg = alert_config.set_config(
        message_template=data.get("message_template"),
        include_frame_with_whatsapp=data.get("include_frame_with_whatsapp"),
        public_base_url=data.get("public_base_url"),
    )
    return jsonify(cfg)


@app.route('/api/analytics/alert-frame')
def analytics_alert_frame():
    """Serve the latest saved alert frame (for WhatsApp media). Twilio fetches this URL; must be publicly reachable."""
    import os
    analytics_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analytics")
    path = os.path.join(analytics_dir, "alert_frames", "latest.jpg")
    if not os.path.isfile(path):
        return "", 404
    return send_file(path, mimetype="image/jpeg", max_age=0)


@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    # Check if ffmpeg is available
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            timeout=2
        )
        ffmpeg_available = result.returncode == 0
    except:
        ffmpeg_available = False
    
    # Check if YOLO is available
    yolo_available = False
    try:
        from ultralytics import YOLO
        yolo_available = True
    except:
        pass
    
    return jsonify({
        "status": "ok",
        "ffmpeg": "available" if ffmpeg_available else "not found",
        "yolo": "available" if yolo_available else "not installed"
    })

if __name__ == '__main__':
    print("=" * 60)
    print("RTSP Stream Viewer with YOLO Object Detection")
    print("=" * 60)

    # Init analytics DB
    try:
        from analytics import db as analytics_db
        analytics_db.init_db()
        print("   Analytics DB: ready (dashboard at /dashboard)")
    except Exception as e:
        print(f"   Analytics: {e}")

    # Pre-load custom 10-class model only (never COCO)
    m = load_yolo_model()
    if m is None:
        print("")
        print("⚠️  No custom model loaded. Streams will show VIDEO ONLY (no boxes).")
        print("   To get detection: ensure custom weights exist at:")
        print(f"   {_model_weights_path()}")
        print("   Then restart this server.")
    else:
        print("   On the video you should see green text: 'Model: custom 10-class'")
        print("   If you see 'potted plant' / 'couch' instead, you're on an OLD server – kill it and use this one.")
    print("")
    print("Make sure ffmpeg is installed: brew install ffmpeg")
    print("Access the viewer at: http://localhost:5001")
    print("Analytics dashboard: http://localhost:5001/dashboard")
    print("=" * 60)
    app.run(port=5001, debug=True, threaded=True)
