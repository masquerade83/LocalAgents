#!/bin/bash
# Frame collection with URL-encoded password
# This handles the @ symbol in the password correctly

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

# Test connection first with ffprobe
echo "Testing connection..."
ffprobe -rtsp_transport tcp -i "$RTSP_URL" -v error -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Connection successful! Starting frame collection..."
    echo ""
    
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
    else
        echo "❌ No frames captured."
    fi
else
    echo "❌ Connection failed. Trying alternative methods..."
    echo ""
    echo "Trying UDP transport..."
    ffmpeg \
        -rtsp_transport udp \
        -i "$RTSP_URL" \
        -vf "fps=1/$FRAME_INTERVAL" \
        -frames:v "$MAX_FRAMES" \
        -f image2 \
        -q:v 2 \
        "$OUTPUT_DIR/frame_%06d.jpg"
    
    FRAME_COUNT=$(ls -1 "$OUTPUT_DIR"/*.jpg 2>/dev/null | wc -l | tr -d ' ')
    if [ "$FRAME_COUNT" -gt 0 ]; then
        echo "✅ Success with UDP! Captured $FRAME_COUNT frames"
    else
        echo "❌ Both TCP and UDP failed."
        echo ""
        echo "Run diagnostic: python3 diagnose_rtsp.py"
    fi
fi
