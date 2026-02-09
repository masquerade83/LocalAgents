#!/usr/bin/env python3
"""
Collect training frames using the working Flask server method
Since the browser viewer works, we'll use the same connection approach
"""

import requests
import os
import time
from datetime import datetime

# Configuration
RTSP_URL = 'rtsp://kush.sood:admin@123@192.168.29.221/stream1'
OUTPUT_DIR = 'dataset/images'
FRAME_INTERVAL = 2  # Capture frame every N seconds
MAX_FRAMES = 100  # Start with 100 for testing
SERVER_URL = 'http://localhost:5001'  # Your working Flask server

def collect_frames_from_server():
    """
    Collect frames by requesting them from the working Flask server
    This uses the same connection method that works in your browser
    """
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=" * 60)
    print("RTSP Frame Collector (via Flask Server)")
    print("=" * 60)
    print(f"RTSP URL: {RTSP_URL}")
    print(f"Server: {SERVER_URL}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Frame interval: {FRAME_INTERVAL} seconds")
    print(f"Max frames: {MAX_FRAMES}")
    print("=" * 60)
    print("\n⚠️  Make sure the Flask server is running!")
    print("   Start it with: cd ../ && python3 server_yolo.py")
    print("   Or: ./start_yolo.sh")
    print("=" * 60)
    print("\nPress Ctrl+C to stop collection\n")
    
    # Check if server is running
    try:
        response = requests.get(f"{SERVER_URL}/api/stream/status", timeout=2)
        if response.status_code != 200:
            print("⚠️  Server might not be running or accessible")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Flask server!")
        print(f"   Make sure it's running at {SERVER_URL}")
        print("\n   Start it with:")
        print("   cd /Users/shailja/clawd/object_detection_working")
        print("   python3 server_yolo.py")
        return
    except Exception as e:
        print(f"⚠️  Server check failed: {e}")
        print("   Continuing anyway...")
    
    # URL encode the RTSP URL for the API
    import urllib.parse
    encoded_rtsp = urllib.parse.quote(RTSP_URL, safe='')
    
    # MJPEG stream endpoint (without YOLO for faster collection)
    stream_url = f"{SERVER_URL}/api/stream/mjpeg?url={encoded_rtsp}&yolo=false"
    
    print(f"✅ Connecting to stream...")
    print(f"   Stream URL: {stream_url}")
    print()
    
    frame_count = 0
    last_capture_time = 0
    
    # First, test if the server can actually connect to RTSP
    print("Testing server connection to RTSP stream...")
    test_url = f"{SERVER_URL}/api/stream/status"
    try:
        test_response = requests.get(test_url, timeout=5)
        print("✅ Server is responding")
    except Exception as e:
        print(f"⚠️  Server status check failed: {e}")
    
    # Try to get a single frame first to test connection
    print("Testing RTSP stream connection (getting one frame)...")
    try:
        test_frame_url = f"{SERVER_URL}/api/stream/mjpeg?url={encoded_rtsp}&yolo=false"
        test_response = requests.get(test_frame_url, stream=True, timeout=60)
        
        if test_response.status_code != 200:
            print(f"❌ Server returned error: {test_response.status_code}")
            print(f"   {test_response.text[:500]}")
            print("\n⚠️  The Flask server cannot connect to the RTSP stream.")
            print("   This is likely the same 'Operation not permitted' issue.")
            print("\n   Try:")
            print("   1. Restart the Flask server in your terminal (it might have permissions)")
            print("   2. Check macOS System Preferences → Security & Privacy")
            print("   3. Or use a different collection method (see TROUBLESHOOTING.md)")
            return
        
        # Try to read a small chunk to see if data is flowing
        chunk = next(test_response.iter_content(chunk_size=1024), None)
        if not chunk:
            print("❌ No data received from server")
            print("   The server cannot connect to RTSP stream")
            return
        
        print("✅ Server can connect to RTSP! Starting collection...\n")
        test_response.close()
    except requests.exceptions.ReadTimeout:
        print("❌ Connection timeout - server cannot connect to RTSP stream")
        print("\n   The Flask server is having the same 'Operation not permitted' issue.")
        print("   The server's ffmpeg process is being blocked by macOS.")
        print("\n   Solutions:")
        print("   1. Restart Flask server in Terminal (might have different permissions)")
        print("   2. Grant network permissions to Python/ffmpeg in System Preferences")
        print("   3. Try running Flask server with sudo (not recommended but might work)")
        return
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        print("   The server might not be able to connect to RTSP")
        return
    
    try:
        # Request the MJPEG stream
        print("Connecting to stream for collection...")
        response = requests.get(stream_url, stream=True, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ Failed to connect: {response.status_code}")
            print(f"   {response.text}")
            return
        
        print("✅ Connected! Starting frame collection...\n")
        
        # Read MJPEG stream
        buffer = b''
        boundary = b'--frame'
        
        for chunk in response.iter_content(chunk_size=1024):
            if frame_count >= MAX_FRAMES:
                break
            
            buffer += chunk
            
            # Look for JPEG end marker
            if b'\xff\xd9' in buffer:
                # Find the start of the JPEG (after boundary and headers)
                jpeg_start = buffer.find(b'\xff\xd8')
                if jpeg_start != -1:
                    jpeg_end = buffer.find(b'\xff\xd9', jpeg_start) + 2
                    
                    if jpeg_end > jpeg_start:
                        current_time = time.time()
                        
                        # Capture at specified interval
                        if current_time - last_capture_time >= FRAME_INTERVAL:
                            jpeg_data = buffer[jpeg_start:jpeg_end]
                            
                            # Generate filename
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                            filename = f"frame_{timestamp}_{frame_count:06d}.jpg"
                            filepath = os.path.join(OUTPUT_DIR, filename)
                            
                            # Save frame
                            with open(filepath, 'wb') as f:
                                f.write(jpeg_data)
                            
                            frame_count += 1
                            last_capture_time = current_time
                            
                            print(f"✅ Captured frame {frame_count}/{MAX_FRAMES}: {filename}")
                        
                        # Clear buffer up to the end of this frame
                        buffer = buffer[jpeg_end:]
            
            # Prevent buffer from growing too large
            if len(buffer) > 1024 * 1024:  # 1MB max
                # Try to find a JPEG start to reset
                jpeg_start = buffer.find(b'\xff\xd8')
                if jpeg_start != -1:
                    buffer = buffer[jpeg_start:]
                else:
                    buffer = b''
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Collection stopped by user")
    except Exception as e:
        print(f"\n❌ Error during collection: {e}")
        import traceback
        traceback.print_exc()
    finally:
        final_count = len([f for f in os.listdir(OUTPUT_DIR) 
                          if f.endswith('.jpg')])
        print(f"\n✅ Collection complete!")
        print(f"   Total frames captured: {final_count}")
        print(f"   Saved to: {os.path.abspath(OUTPUT_DIR)}")

if __name__ == '__main__':
    collect_frames_from_server()
