"""
Background capture: connect to RTSP, run YOLO at fixed interval, store detections and evaluate triggers.
"""
import os
import subprocess
import threading
import time
import numpy as np

# Parent dir for server's load_yolo_model
_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_one_jpeg(stream):
    SOI, EOI = b'\xff\xd8', b'\xff\xd9'
    buf = b''
    while True:
        chunk = stream.read(4096)
        if not chunk:
            return None
        buf += chunk
        start = buf.find(SOI)
        if start == -1:
            buf = buf[-1:]
            continue
        end = buf.find(EOI, start)
        if end == -1:
            buf = buf[start:]
            continue
        return buf[start : end + 2]


def run_analytics_capture(rtsp_url: str, stream_id: str, model, interval_sec: float = 1.0, confidence: float = 0.25, stop_event: threading.Event = None):
    """
    Run in a thread. Reads MJPEG from ffmpeg, runs YOLO every interval_sec, inserts into DB and checks triggers.
    Stops when stop_event is set.
    """
    import cv2
    # Ensure .env is loaded in this thread so TWILIO_* etc. are available for WhatsApp alerts
    env_path = os.path.join(_parent, ".env")
    if os.path.isfile(env_path):
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
    from . import db
    from . import triggers

    cmd = [
        "ffmpeg", "-rtsp_transport", "tcp", "-i", rtsp_url,
        "-vf", "fps=1,scale=1280:720", "-q:v", "3", "-f", "mjpeg", "-"
    ]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10**8)
    except Exception as e:
        print(f"[Analytics] Capture failed to start ffmpeg: {e}")
        return

    stop = stop_event or threading.Event()
    frame_count = 0

    try:
        while not stop.is_set():
            jpeg_bytes = _read_one_jpeg(proc.stdout)
            if jpeg_bytes is None:
                break
            frame = cv2.imdecode(np.frombuffer(jpeg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                continue

            ts = time.time()
            results = model(frame, conf=confidence, imgsz=640, verbose=False)
            r = results[0]
            detections = []
            if r.boxes is not None and len(r.boxes):
                cls_ids = r.boxes.cls.cpu().numpy().astype(int)
                confs = r.boxes.conf.cpu().numpy()
                for cid, conf in zip(cls_ids, confs):
                    class_name = model.names.get(int(cid), f"cls_{cid}")
                    detections.append({"class_name": class_name, "confidence": float(conf)})
                    db.insert_detection(stream_id, rtsp_url, class_name, float(conf), ts)

            if detections:
                triggers.check_triggers(stream_id, detections, frame=frame)

            frame_count += 1
            # Sleep so we don't run faster than interval_sec
            elapsed = time.time() - (ts - interval_sec)
            if elapsed < interval_sec:
                time.sleep(interval_sec - elapsed)
    except Exception as e:
        print(f"[Analytics] Capture error: {e}")
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    print(f"[Analytics] Capture stopped for {stream_id} ({frame_count} frames)")


# Global state for one analytics stream
_analytics_state = {"running": False, "stream_id": None, "thread": None, "stop_event": None}
_analytics_lock = threading.Lock()


def start_capture(rtsp_url: str, model, stream_id: str = None, interval_sec: float = 1.0, confidence: float = 0.25):
    with _analytics_lock:
        if _analytics_state["running"]:
            return False, "Analytics capture already running"
        if stream_id is None:
            stream_id = rtsp_url
        _analytics_state["stop_event"] = threading.Event()
        _analytics_state["stream_id"] = stream_id
        _analytics_state["thread"] = threading.Thread(
            target=run_analytics_capture,
            args=(rtsp_url, stream_id, model),
            kwargs={"interval_sec": interval_sec, "confidence": confidence, "stop_event": _analytics_state["stop_event"]},
            daemon=True,
        )
        _analytics_state["running"] = True
        _analytics_state["thread"].start()
        return True, "Started"


def stop_capture():
    with _analytics_lock:
        if not _analytics_state["running"]:
            return False, "Not running"
        _analytics_state["stop_event"].set()
        _analytics_state["thread"].join(timeout=15)
        _analytics_state["running"] = False
        _analytics_state["thread"] = None
        _analytics_state["stream_id"] = None
        return True, "Stopped"


def is_capture_running():
    with _analytics_lock:
        return _analytics_state["running"], _analytics_state.get("stream_id")
