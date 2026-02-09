#!/bin/bash
# Start RTSP Viewer with YOLO Detection

echo "Starting RTSP Viewer with YOLO..."
echo ""

# Check if ultralytics is installed
if ! python3 -c "import ultralytics" 2>/dev/null; then
    echo "Installing YOLO dependencies..."
    pip3 install -r requirements_yolo.txt
    echo ""
fi

# Check if opencv is installed
if ! python3 -c "import cv2" 2>/dev/null; then
    echo "Installing OpenCV..."
    pip3 install opencv-python
    echo ""
fi

echo "Starting server on http://localhost:5001"
echo "Press Ctrl+C to stop"
echo ""

python3 server_yolo.py
