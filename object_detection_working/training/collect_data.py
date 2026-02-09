#!/usr/bin/env python3
"""
Collect training data from RTSP stream
Captures frames for annotation and training
Uses ffmpeg for reliable RTSP connection
"""

import cv2
import os
import time
import subprocess
import numpy as np
from datetime import datetime

# Configuration
# NOTE: Password contains @ symbol, so we need to URL-encode it
# admin@123 -> admin%40123
RTSP_URL = 'rtsp://kush.sood:admin%40123@192.168.29.221/stream1'
OUTPUT_DIR = 'dataset/images'
FRAME_INTERVAL = 2  # Capture frame every N seconds
MAX_FRAMES = 1000  # Maximum frames to collect

def collect_frames_ffmpeg():
    """Capture frames from RTSP stream using ffmpeg (more reliable)"""
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 60)
    print("RTSP Frame Collector for Training Data")
    print("=" * 60)
    print(f"RTSP URL: {RTSP_URL}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Frame interval: {FRAME_INTERVAL} seconds")
    print(f"Max frames: {MAX_FRAMES}")
    print("=" * 60)
    print("\nPress Ctrl+C to stop collection\n")
    
    # Use ffmpeg to capture frames (more reliable than OpenCV for RTSP)
    # Capture frames at specified interval
    cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',  # Use TCP for reliability
        '-i', RTSP_URL,
        '-vf', f'fps=1/{FRAME_INTERVAL}',  # Capture 1 frame every FRAME_INTERVAL seconds
        '-frames:v', str(MAX_FRAMES),  # Maximum frames
        '-f', 'image2',  # Output as images
        '-q:v', '2',  # High quality (1-31, lower is better)
        os.path.join(OUTPUT_DIR, 'frame_%06d.jpg')  # Output pattern
    ]
    
    try:
        print("✅ Starting frame capture with ffmpeg...")
        print("   This may take a while depending on MAX_FRAMES and FRAME_INTERVAL\n")
        
        # Run ffmpeg and show output in real-time
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Wait for process to finish
        stdout, stderr = process.communicate()
        
        # Count actual files created
        final_count = len([f for f in os.listdir(OUTPUT_DIR) 
                          if f.endswith('.jpg')])
        
        # Show progress during collection
        if final_count > 0:
            print(f"✅ Captured {final_count}/{MAX_FRAMES} frames...")
        
        if process.returncode == 0:
            print(f"\n✅ Collection complete!")
            print(f"   Total frames captured: {final_count}")
            print(f"   Saved to: {os.path.abspath(OUTPUT_DIR)}")
        else:
            print(f"\n⚠️  Process ended with code {process.returncode}")
            stderr_output = stderr if stderr else ""
            
            # Check for permission errors
            if 'Operation not permitted' in stderr_output or 'operation not permitted' in stderr_output.lower():
                print("\n❌ Network permission error detected")
                print("   This usually means you need to run this script in your terminal")
                print("   (not through automated tools)")
                print("\n   Please run manually:")
                print(f"   cd {os.path.abspath('.')}")
                print(f"   python3 collect_data.py")
                print("\n   Or use the manual command:")
                print(f"   {' '.join(cmd)}")
            else:
                if stderr_output:
                    error_msg = stderr_output[-500:] if len(stderr_output) > 500 else stderr_output
                    print(f"   Error: {error_msg}")
            
            if final_count > 0:
                print(f"\n✅ Captured {final_count} frames before error")
                print(f"   Saved to: {os.path.abspath(OUTPUT_DIR)}")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Collection stopped by user")
        try:
            if 'process' in locals():
                process.terminate()
                process.wait(timeout=5)
        except:
            if 'process' in locals():
                process.kill()
        
        final_count = len([f for f in os.listdir(OUTPUT_DIR) 
                          if f.endswith('.jpg')])
        print(f"\n✅ Saved {final_count} frames before stopping")
        print(f"   Saved to: {os.path.abspath(OUTPUT_DIR)}")
        
    except Exception as e:
        print(f"\n❌ Error during collection: {e}")
        final_count = len([f for f in os.listdir(OUTPUT_DIR) 
                          if f.endswith('.jpg')])
        if final_count > 0:
            print(f"   Saved {final_count} frames before error")

def collect_frames_opencv():
    """Alternative method using OpenCV (less reliable for RTSP)"""
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 60)
    print("RTSP Frame Collector (OpenCV method)")
    print("=" * 60)
    print(f"RTSP URL: {RTSP_URL}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Frame interval: {FRAME_INTERVAL} seconds")
    print(f"Max frames: {MAX_FRAMES}")
    print("=" * 60)
    print("\nPress Ctrl+C to stop collection\n")
    
    # Try OpenCV as fallback
    cap = cv2.VideoCapture(RTSP_URL)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    if not cap.isOpened():
        print(f"❌ Error: Could not open RTSP stream with OpenCV")
        print("   Trying ffmpeg method instead...")
        return collect_frames_ffmpeg()
    
    print("✅ Connected to stream")
    print("Starting frame collection...\n")
    
    frame_count = 0
    last_capture_time = 0
    
    try:
        while frame_count < MAX_FRAMES:
            ret, frame = cap.read()
            
            if not ret:
                print("⚠️  Failed to read frame, retrying...")
                time.sleep(1)
                continue
            
            current_time = time.time()
            
            # Capture frame at specified interval
            if current_time - last_capture_time >= FRAME_INTERVAL:
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"frame_{timestamp}_{frame_count:06d}.jpg"
                filepath = os.path.join(OUTPUT_DIR, filename)
                
                # Save frame
                cv2.imwrite(filepath, frame)
                frame_count += 1
                last_capture_time = current_time
                
                print(f"✅ Captured frame {frame_count}/{MAX_FRAMES}: {filename}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Collection stopped by user")
    except Exception as e:
        print(f"\n❌ Error during collection: {e}")
    finally:
        cap.release()
        print(f"\n✅ Collection complete!")
        print(f"   Total frames captured: {frame_count}")
        print(f"   Saved to: {os.path.abspath(OUTPUT_DIR)}")

def collect_frames():
    """Main function - tries ffmpeg first (more reliable)"""
    print("\n" + "=" * 60)
    print("IMPORTANT: If you get 'Operation not permitted' error,")
    print("please run this script in your terminal manually:")
    print(f"  cd {os.path.abspath('.')}")
    print("  python3 collect_data.py")
    print("=" * 60 + "\n")
    
    # Use ffmpeg method (more reliable for RTSP)
    collect_frames_ffmpeg()

if __name__ == '__main__':
    collect_frames()
