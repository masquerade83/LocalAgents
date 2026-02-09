# RTSP Stream Viewer with YOLO Object Detection - Working Copy

This is a working copy of the RTSP stream viewer with real-time YOLO object detection.

## Status: ✅ Working

All files in this directory are confirmed working and tested.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements_yolo.txt
   ```

2. **Start the server:**
   ```bash
   python3 server_yolo.py
   ```
   Or use the startup script:
   ```bash
   ./start_yolo.sh
   ```

3. **Open in browser:**
   ```
   http://localhost:5001
   ```

4. **Connect to stream:**
   - Enter RTSP URL: `rtsp://kush.sood:admin@123@192.168.29.221/stream1`
   - Enable YOLO Detection (checkbox)
   - Adjust confidence if needed
   - Click Connect

## Files Included

- `server_yolo.py` - Main server with YOLO integration
- `index.html` - Web interface
- `app.js` - Frontend JavaScript
- `styles.css` - Styling
- `requirements_yolo.txt` - Python dependencies
- `start_yolo.sh` - Quick start script
- `test_yolo_connection.py` - Connection test script
- `README_YOLO.md` - Detailed documentation

## Features

- ✅ Real-time RTSP stream viewing
- ✅ YOLOv8 object detection
- ✅ Adjustable confidence threshold
- ✅ Visual annotations (bounding boxes + labels)
- ✅ Toggle YOLO on/off
- ✅ Clean, modern UI

## Tested Configuration

- **RTSP Stream**: `rtsp://kush.sood:admin@123@192.168.29.221/stream1`
- **YOLO Model**: YOLOv8n (nano)
- **Frame Rate**: 10 FPS
- **Resolution**: Max 1280px width (auto-scaled)
- **Status**: Working perfectly ✅

## Notes

- First run will download YOLO model (~6MB)
- Stream uses ffmpeg for reliable RTSP decoding
- Processing happens in real-time
- All dependencies are documented in requirements_yolo.txt

---

**Created**: 2026-01-26  
**Status**: Production Ready ✅
