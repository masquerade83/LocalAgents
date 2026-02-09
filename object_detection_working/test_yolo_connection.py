#!/usr/bin/env python3
"""
Test script to verify RTSP stream and YOLO setup
"""

import subprocess
import sys

rtsp_url = 'rtsp://kush.sood:admin@123@192.168.29.221/stream1'

print("Testing RTSP Stream with YOLO")
print("=" * 60)

# Test 1: Check ffmpeg
print("\n1. Checking ffmpeg...")
try:
    result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=2)
    if result.returncode == 0:
        print("   ✅ ffmpeg is available")
    else:
        print("   ❌ ffmpeg not working")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ ffmpeg not found: {e}")
    sys.exit(1)

# Test 2: Check if we can read RTSP stream with ffmpeg
print("\n2. Testing RTSP stream connection...")
cmd = [
    'ffmpeg',
    '-rtsp_transport', 'tcp',
    '-i', rtsp_url,
    '-frames:v', '1',  # Just get 1 frame
    '-f', 'image2',
    '-'
]

try:
    result = subprocess.run(cmd, capture_output=True, timeout=10)
    if result.returncode == 0:
        print("   ✅ RTSP stream is accessible")
        print(f"   Got {len(result.stdout)} bytes of frame data")
    else:
        print("   ❌ Cannot read RTSP stream")
        print("   Error:", result.stderr.decode()[-200:])
except subprocess.TimeoutExpired:
    print("   ⚠️  Connection timeout (stream might be slow)")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Check YOLO
print("\n3. Checking YOLO...")
try:
    from ultralytics import YOLO
    print("   ✅ Ultralytics is installed")
    try:
        model = YOLO('yolov8n.pt')
        print("   ✅ YOLO model loaded successfully")
    except Exception as e:
        print(f"   ⚠️  YOLO model not loaded: {e}")
except ImportError:
    print("   ❌ Ultralytics not installed")
    print("   Install with: pip install ultralytics")

# Test 4: Check OpenCV
print("\n4. Checking OpenCV...")
try:
    import cv2
    print(f"   ✅ OpenCV version {cv2.__version__}")
except ImportError:
    print("   ❌ OpenCV not installed")
    print("   Install with: pip install opencv-python")

print("\n" + "=" * 60)
print("Setup check complete!")
print("\nTo start the server:")
print("  python3 server_yolo.py")
