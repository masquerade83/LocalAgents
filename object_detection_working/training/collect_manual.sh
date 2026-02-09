#!/bin/bash
# Manual frame collection script - run this in your terminal

RTSP_URL="rtsp://kush.sood:admin@123@192.168.29.221/stream1"
OUTPUT_DIR="dataset/images"
FRAME_INTERVAL=2
MAX_FRAMES=100

echo "RTSP Frame Collector (Manual)"
echo "=============================="
echo ""
echo "This script will capture frames from your RTSP stream"
echo "RTSP URL: $RTSP_URL"
echo "Output: $OUTPUT_DIR"
echo "Interval: $FRAME_INTERVAL seconds"
echo "Max frames: $MAX_FRAMES"
echo ""
read -p "Press Enter to start (or Ctrl+C to cancel)..."

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Use ffmpeg to capture frames
ffmpeg \
    -rtsp_transport tcp \
    -i "$RTSP_URL" \
    -vf "fps=1/$FRAME_INTERVAL" \
    -frames:v "$MAX_FRAMES" \
    -f image2 \
    -q:v 2 \
    "$OUTPUT_DIR/frame_%06d.jpg"

# Count captured frames
FRAME_COUNT=$(ls -1 "$OUTPUT_DIR"/*.jpg 2>/dev/null | wc -l)

echo ""
echo "✅ Collection complete!"
echo "   Captured $FRAME_COUNT frames"
echo "   Saved to: $(pwd)/$OUTPUT_DIR"
