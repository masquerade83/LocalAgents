# RTSP Stream Viewer with YOLO Object Detection

Enhanced version of the RTSP viewer with real-time object detection using YOLOv8.

## Features

- 🎯 **Real-time Object Detection** - YOLOv8 detects objects in the video stream
- 📦 **80+ Object Classes** - Detects people, vehicles, animals, and more
- 🎨 **Visual Annotations** - Bounding boxes and labels drawn on detected objects
- ⚙️ **Adjustable Confidence** - Control detection sensitivity
- 🔄 **Toggle Detection** - Enable/disable YOLO on the fly

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements_yolo.txt
   ```

   Or install manually:
   ```bash
   pip install ultralytics opencv-python flask flask-cors numpy
   ```

2. **YOLO Model Download:**
   - The model (`yolov8n.pt`) will be automatically downloaded on first run
   - This is the "nano" model - fastest but less accurate
   - You can change to `yolov8s.pt`, `yolov8m.pt`, etc. in `server_yolo.py` for better accuracy

## Usage

1. **Start the server:**
   ```bash
   python3 server_yolo.py
   ```

2. **Open in browser:**
   ```
   http://localhost:5001
   ```

3. **Configure detection:**
   - Check/uncheck "YOLO Detection" to enable/disable
   - Adjust confidence slider (0.1 - 0.9)
     - Lower = more detections (more false positives)
     - Higher = fewer detections (more accurate)

4. **Enter RTSP URL and connect**

## YOLO Model Options

Edit `server_yolo.py` line ~30 to change model:

- `yolov8n.pt` - Nano (fastest, ~6MB)
- `yolov8s.pt` - Small (balanced, ~22MB)
- `yolov8m.pt` - Medium (better accuracy, ~52MB)
- `yolov8l.pt` - Large (high accuracy, ~88MB)
- `yolov8x.pt` - Extra Large (best accuracy, ~136MB)

## Detected Objects

YOLOv8 can detect 80+ object classes including:
- People, faces
- Vehicles (cars, trucks, buses, motorcycles, bicycles)
- Animals (dogs, cats, birds, horses, etc.)
- Common objects (chairs, tables, phones, laptops, etc.)
- Sports equipment
- And more!

## Performance Tips

1. **Use YOLOv8n** for fastest performance (default)
2. **Lower FPS** - Edit `fps=10` in server_yolo.py to reduce processing
3. **Process every N frames** - Change `frame_count % 1` to `frame_count % 2` to process every 2nd frame
4. **Reduce resolution** - Change `scale=1280:-1` to smaller (e.g., `scale=640:-1`)

## Troubleshooting

### YOLO not working
- Make sure ultralytics is installed: `pip install ultralytics`
- Check that model downloads successfully (first run)
- Look for error messages in server console

### Slow performance
- Use YOLOv8n (nano) model
- Reduce frame processing rate
- Lower resolution
- Increase confidence threshold to reduce detections

### No detections
- Lower confidence threshold (try 0.1-0.2)
- Check that objects are clearly visible
- Ensure good lighting in video

## File Structure

```
rtsp-viewer/
├── server_yolo.py      # Server with YOLO integration
├── server.py           # Original server (no YOLO)
├── index.html          # UI (updated with YOLO controls)
├── app.js              # Frontend (updated)
├── styles.css          # Styling (updated)
└── requirements_yolo.txt  # YOLO dependencies
```

## Notes

- First run will download YOLO model (~6MB for nano)
- Processing happens in real-time (may add slight latency)
- GPU acceleration available if CUDA is installed
- CPU-only mode works but is slower
