#!/bin/bash
# Capture ADDITIONAL frames without overwriting existing ones.
# New frames are merged into dataset/images with continued numbering.
# Run this script in your Terminal (ffmpeg needs network permission).

RTSP_URL="rtsp://kush.sood:admin%40123@192.168.29.221/stream1"
OUTPUT_DIR="dataset/images"
APPEND_DIR="dataset/images_append"
FRAME_INTERVAL=2
MAX_FRAMES=100

# Find next frame number from existing images
CURRENT_MAX=$(ls -1 "$OUTPUT_DIR"/frame_*.jpg 2>/dev/null | sed 's/.*frame_0*\([0-9]*\)\.jpg/\1/' | sort -n | tail -1)
START=$((CURRENT_MAX + 1))
END=$((START + MAX_FRAMES - 1))

echo "=============================================="
echo "Collecting MORE frames (append to existing)"
echo "=============================================="
echo "RTSP: $RTSP_URL"
echo "Existing frames: ${CURRENT_MAX:-0}"
echo "New frames: $MAX_FRAMES (will be numbered $START to $END)"
echo "Output: $OUTPUT_DIR"
echo "=============================================="
echo ""

mkdir -p "$APPEND_DIR"
rm -f "$APPEND_DIR"/frame_*.jpg 2>/dev/null

# Capture to temp dir with simple numbering
ffmpeg -y -rtsp_transport tcp -i "$RTSP_URL" \
    -vf "fps=1/$FRAME_INTERVAL" \
    -frames:v "$MAX_FRAMES" \
    -f image2 -q:v 2 \
    "$APPEND_DIR/frame_%06d.jpg" 2>/dev/null

# Rename and move into main folder (continue numbering)
COUNT=0
for f in $(ls -1 "$APPEND_DIR"/frame_*.jpg 2>/dev/null | sort -V); do
  [ -f "$f" ] || continue
  num=$(printf "%06d" $START)
  mv "$f" "$OUTPUT_DIR/frame_${num}.jpg"
  START=$((START + 1))
  COUNT=$((COUNT + 1))
done

rmdir "$APPEND_DIR" 2>/dev/null
TOTAL=$(ls -1 "$OUTPUT_DIR"/frame_*.jpg 2>/dev/null | wc -l | tr -d ' ')

echo ""
echo "✅ Added $COUNT frames. Total in dataset/images: $TOTAL"
echo ""
echo "Next: python3 split_dataset.py   (then annotate new images if needed)"
echo ""
