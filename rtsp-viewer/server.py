#!/usr/bin/env python3
"""
RTSP Stream Viewer Backend
Converts RTSP streams to browser-compatible formats (MJPEG/HLS)
"""

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
import subprocess
import threading
import os
import signal
import time

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Store active stream processes
active_streams = {}
stream_lock = threading.Lock()

def create_mjpeg_stream(rtsp_url):
    """
    Create MJPEG stream from RTSP using ffmpeg
    Returns a generator that yields JPEG frames
    """
    # FFmpeg command to convert RTSP to MJPEG
    # -rtsp_transport tcp: Use TCP for RTSP (more reliable)
    # -i: Input RTSP URL
    # -vf fps=10: Set frame rate to 10 FPS
    # -q:v 5: JPEG quality (2-31, lower is better)
    # -f mjpeg: Output format as MJPEG
    # -: Output to stdout
    cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,
        '-vf', 'fps=10,scale=1280:-1',  # 10 FPS, scale to 1280px width
        '-q:v', '5',  # Good quality
        '-f', 'mjpeg',
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
            try:
                while True:
                    # Read JPEG frame (JPEG files start with 0xFF 0xD8)
                    chunk = process.stdout.read(1024)
                    if not chunk:
                        break
                    
                    # Accumulate JPEG data
                    frame = chunk
                    while True:
                        chunk = process.stdout.read(1024)
                        if not chunk:
                            break
                        frame += chunk
                        # Check if we have a complete JPEG (ends with 0xFF 0xD9)
                        if frame[-2:] == b'\xff\xd9':
                            break
                    
                    # Yield frame with proper headers
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

@app.route('/api/stream/start', methods=['POST'])
def start_stream():
    """Start an RTSP stream"""
    data = request.json
    rtsp_url = data.get('url')
    
    if not rtsp_url:
        return jsonify({"error": "RTSP URL is required"}), 400
    
    if not rtsp_url.startswith('rtsp://'):
        return jsonify({"error": "Invalid RTSP URL format"}), 400
    
    stream_id = rtsp_url  # Use URL as stream ID
    
    with stream_lock:
        if stream_id in active_streams:
            return jsonify({
                "message": "Stream already active",
                "stream_url": f"/api/stream/mjpeg?url={stream_id}",
                "format": "MJPEG"
            })
        
        # Store stream info
        active_streams[stream_id] = {
            "url": rtsp_url,
            "started": time.time()
        }
    
    return jsonify({
        "message": "Stream started",
        "stream_url": f"/api/stream/mjpeg?url={stream_id}",
        "format": "MJPEG"
    })

@app.route('/api/stream/stop', methods=['POST'])
def stop_stream():
    """Stop all active streams"""
    with stream_lock:
        active_streams.clear()
    
    return jsonify({"message": "All streams stopped"})

@app.route('/api/stream/mjpeg')
def mjpeg_stream():
    """MJPEG stream endpoint"""
    stream_url = request.args.get('url')
    
    if not stream_url:
        return jsonify({"error": "Stream URL parameter required"}), 400
    
    # Decode URL if needed
    try:
        import urllib.parse
        rtsp_url = urllib.parse.unquote(stream_url)
    except:
        rtsp_url = stream_url
    
    return Response(
        create_mjpeg_stream(rtsp_url),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/stream/status', methods=['GET'])
def stream_status():
    """Get status of active streams"""
    with stream_lock:
        streams = list(active_streams.keys())
    
    return jsonify({
        "active_streams": len(streams),
        "streams": streams
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
    
    return jsonify({
        "status": "ok",
        "ffmpeg": "available" if ffmpeg_available else "not found"
    })

if __name__ == '__main__':
    print("=" * 60)
    print("RTSP Stream Viewer Server")
    print("=" * 60)
    print("Make sure ffmpeg is installed:")
    print("  brew install ffmpeg")
    print("")
    print("Access the viewer at: http://localhost:5001")
    print("=" * 60)
    app.run(port=5001, debug=True, threaded=True)
