#!/bin/bash
# Simple frame collection - just run this in your terminal

# URL-encode the @ in password: admin@123 -> admin%40123
RTSP_URL="rtsp://kush.sood:admin%40123@192.168.29.221/stream1"
OUTPUT_DIR="dataset/images"
FRAME_INTERVAL=2
MAX_FRAMES=100

echo "Collecting frames from RTSP stream..."
echo "RTSP: $RTSP_URL"
echo "Output: $OUTPUT_DIR"
echo "Interval: $FRAME_INTERVAL seconds"
echo "Max frames: $MAX_FRAMES"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run ffmpeg
ffmpeg \
    -rtsp_transport tcp \
    -i "$RTSP_URL" \
    -vf "fps=1/$FRAME_INTERVAL" \
    -frames:v "$MAX_FRAMES" \
    -f image2 \
    -q:v 2 \
    "$OUTPUT_DIR/frame_%06d.jpg"

# Check results
FRAME_COUNT=$(ls -1 "$OUTPUT_DIR"/*.jpg 2>/dev/null | wc -l | tr -d ' ')

echo ""
if [ "$FRAME_COUNT" -gt 0 ]; then
    echo "✅ Success! Captured $FRAME_COUNT frames"
    echo "   Location: $(pwd)/$OUTPUT_DIR"
    echo ""
    echo "Next steps:"
    echo "  1. python3 split_dataset.py"
    echo "  2. Annotate images with LabelImg"
    echo "  3. python3 train_custom_model.py"
else
    echo "❌ No frames captured. Check RTSP URL and network connection."
fi
