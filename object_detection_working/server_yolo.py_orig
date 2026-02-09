#!/usr/bin/env python3
"""
RTSP Stream Viewer with YOLO Object Detection
Converts RTSP streams to browser-compatible formats with real-time object detection
"""

from flask import Flask, Response, jsonify, request, send_from_directory
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

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Store active stream processes
active_streams = {}
stream_lock = threading.Lock()

# Global YOLO model (loaded once)
yolo_model = None
model_lock = threading.Lock()

def load_yolo_model():
    """Load YOLO model (YOLOv8)"""
    global yolo_model
    with model_lock:
        if yolo_model is None:
            try:
                print("Loading YOLO model...")
                # Try to load YOLOv8n (nano - fastest) or YOLOv8s (small)
                # You can change to 'yolov8s.pt', 'yolov8m.pt', etc. for better accuracy
                yolo_model = YOLO('yolov8n.pt')  # nano model for speed
                print("✅ YOLO model loaded successfully")
            except Exception as e:
                print(f"❌ Failed to load YOLO model: {e}")
                print("Make sure ultralytics is installed: pip install ultralytics")
                return None
    return yolo_model

def create_yolo_stream(rtsp_url, confidence=0.25):
    """
    Create annotated MJPEG stream from RTSP using ffmpeg + OpenCV + YOLO
    Uses ffmpeg to decode RTSP (more reliable) then processes with YOLO
    """
    model = load_yolo_model()
    if model is None:
        # Fallback to regular stream if YOLO fails
        return create_mjpeg_stream_fallback(rtsp_url)
    
    import cv2
    import numpy as np
    
    # Use ffmpeg to decode RTSP stream and pipe raw video to OpenCV
    # This is more reliable than OpenCV's VideoCapture for RTSP
    cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',  # Use TCP for reliability
        '-i', rtsp_url,
        '-vf', 'fps=10,scale=1280:-1',  # 10 FPS, scale to 1280px
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',  # BGR format for OpenCV
        '-'  # Output to stdout
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
            width = 1280
            height = 720  # Default, will be detected from first frame
            frame_size = width * height * 3  # 3 channels (BGR)
            first_frame = True
            
            try:
                while True:
                    # Read raw frame from ffmpeg
                    raw_frame = process.stdout.read(frame_size)
                    if len(raw_frame) == 0:
                        break
                    
                    if len(raw_frame) != frame_size:
                        # Frame size mismatch - might be different resolution
                        # Try to detect actual size or skip
                        if first_frame:
                            # Try common resolutions
                            for test_h in [480, 720, 1080]:
                                test_w = 1280
                                test_size = test_w * test_h * 3
                                if len(raw_frame) >= test_size:
                                    height = test_h
                                    width = test_w
                                    frame_size = test_size
                                    break
                            first_frame = False
                        
                        if len(raw_frame) < frame_size:
                            # Still not enough data, skip this frame
                            continue
                        else:
                            # More data than expected, take what we need
                            raw_frame = raw_frame[:frame_size]
                    
                    # Convert to numpy array and reshape
                    frame = np.frombuffer(raw_frame, dtype=np.uint8)
                    frame = frame.reshape((height, width, 3))
                    first_frame = False
                    
                    # Run YOLO detection every frame (or every N frames for performance)
                    if frame_count % 1 == 0:  # Process every frame
                        results = model(frame, conf=confidence, verbose=False)
                        
                        # Draw detections on frame
                        annotated_frame = results[0].plot()
                        frame = annotated_frame
                    
                    # Encode frame as JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    frame_bytes = buffer.tobytes()
                    
                    # Yield frame with proper headers
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    
                    frame_count += 1
                    
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
        print(f"Failed to start ffmpeg for YOLO stream: {e}")
        # Fallback to regular stream
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

@app.route('/api/stream/start', methods=['POST'])
def start_stream():
    """Start an RTSP stream with optional YOLO detection"""
    data = request.json
    rtsp_url = data.get('url')
    use_yolo = data.get('yolo', True)  # Enable YOLO by default
    confidence = data.get('confidence', 0.25)  # Detection confidence threshold
    
    if not rtsp_url:
        return jsonify({"error": "RTSP URL is required"}), 400
    
    if not rtsp_url.startswith('rtsp://'):
        return jsonify({"error": "Invalid RTSP URL format"}), 400
    
    stream_id = rtsp_url
    
    with stream_lock:
        if stream_id in active_streams:
            return jsonify({
                "message": "Stream already active",
                "stream_url": f"/api/stream/mjpeg?url={stream_id}&yolo={use_yolo}",
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
        "stream_url": f"/api/stream/mjpeg?url={stream_id}&yolo={use_yolo}",
        "format": "MJPEG",
        "yolo": use_yolo
    })

@app.route('/api/stream/stop', methods=['POST'])
def stop_stream():
    """Stop all active streams"""
    with stream_lock:
        active_streams.clear()
    
    return jsonify({"message": "All streams stopped"})

@app.route('/api/stream/mjpeg')
def mjpeg_stream():
    """MJPEG stream endpoint with optional YOLO"""
    stream_url = request.args.get('url')
    use_yolo = request.args.get('yolo', 'true').lower() == 'true'
    confidence = float(request.args.get('confidence', 0.25))
    
    if not stream_url:
        return jsonify({"error": "Stream URL parameter required"}), 400
    
    # Decode URL if needed
    try:
        import urllib.parse
        rtsp_url = urllib.parse.unquote(stream_url)
    except:
        rtsp_url = stream_url
    
    if use_yolo:
        return Response(
            create_yolo_stream(rtsp_url, confidence),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    else:
        return Response(
            create_mjpeg_stream_fallback(rtsp_url),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )

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
    
    # Pre-load YOLO model
    load_yolo_model()
    
    print("Make sure ffmpeg is installed:")
    print("  brew install ffmpeg")
    print("")
    print("Install YOLO dependencies:")
    print("  pip install ultralytics opencv-python")
    print("")
    print("Access the viewer at: http://localhost:5001")
    print("=" * 60)
    app.run(port=5001, debug=True, threaded=True)
