#!/usr/bin/env python3
"""
Generate the exact ffmpeg command to collect frames
Run this to get the command, then copy-paste it into your terminal
"""

import os

# Configuration
RTSP_URL = 'rtsp://kush.sood:admin@123@192.168.29.221/stream1'
OUTPUT_DIR = 'dataset/images'
FRAME_INTERVAL = 2
MAX_FRAMES = 100  # Start with 100 for testing

print("=" * 70)
print("RTSP Frame Collection Command Generator")
print("=" * 70)
print()
print("Copy and paste this command into your terminal:")
print()
print("-" * 70)

# Create the command
cmd = f"""cd {os.path.abspath('.')} && mkdir -p {OUTPUT_DIR} && ffmpeg -rtsp_transport tcp -i "{RTSP_URL}" -vf "fps=1/{FRAME_INTERVAL}" -frames:v {MAX_FRAMES} -f image2 -q:v 2 {OUTPUT_DIR}/frame_%06d.jpg"""

print(cmd)
print("-" * 70)
print()
print("Or run it step by step:")
print()
print(f"1. cd {os.path.abspath('.')}")
print(f"2. mkdir -p {OUTPUT_DIR}")
print(f"3. ffmpeg -rtsp_transport tcp -i \"{RTSP_URL}\" -vf \"fps=1/{FRAME_INTERVAL}\" -frames:v {MAX_FRAMES} -f image2 -q:v 2 {OUTPUT_DIR}/frame_%06d.jpg")
print()
print("=" * 70)
print()
print("Parameters:")
print(f"  - Frame interval: {FRAME_INTERVAL} seconds")
print(f"  - Max frames: {MAX_FRAMES}")
print(f"  - Output: {OUTPUT_DIR}/")
print()
print("After collection, run: python3 split_dataset.py")
