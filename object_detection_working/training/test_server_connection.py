#!/usr/bin/env python3
"""
Test if the Flask server can actually connect to RTSP
This helps diagnose if the server has the same permission issues
"""

import requests
import urllib.parse
import sys

SERVER_URL = 'http://localhost:5001'
RTSP_URL = 'rtsp://kush.sood:admin@123@192.168.29.221/stream1'

print("=" * 70)
print("Flask Server RTSP Connection Test")
print("=" * 70)
print()

# Test 1: Is server running?
print("1. Testing if server is running...")
try:
    response = requests.get(f"{SERVER_URL}/api/stream/status", timeout=2)
    if response.status_code == 200:
        print("   ✅ Server is running")
    else:
        print(f"   ⚠️  Server returned: {response.status_code}")
except requests.exceptions.ConnectionError:
    print("   ❌ Server is NOT running!")
    print(f"   Start it with: cd /Users/shailja/clawd/object_detection_working && python3 server_yolo.py")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

print()

# Test 2: Can server connect to RTSP?
print("2. Testing if server can connect to RTSP stream...")
encoded_rtsp = urllib.parse.quote(RTSP_URL, safe='')
stream_url = f"{SERVER_URL}/api/stream/mjpeg?url={encoded_rtsp}&yolo=false"

print(f"   RTSP URL: {RTSP_URL}")
print(f"   Stream endpoint: {stream_url}")
print()

try:
    print("   Attempting connection (10 second timeout)...")
    response = requests.get(stream_url, stream=True, timeout=10)
    
    if response.status_code != 200:
        print(f"   ❌ Server returned error: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        sys.exit(1)
    
    print("   ✅ HTTP connection successful")
    print("   Reading stream data...")
    
    # Try to read some data
    data_received = False
    chunk_count = 0
    
    for chunk in response.iter_content(chunk_size=1024):
        chunk_count += 1
        if chunk:
            data_received = True
            print(f"   ✅ Received {len(chunk)} bytes of data (chunk {chunk_count})")
            if chunk_count >= 3:  # Got a few chunks, that's enough
                break
        if chunk_count > 10:  # Safety limit
            break
    
    response.close()
    
    if data_received:
        print()
        print("=" * 70)
        print("✅ SUCCESS! Server CAN connect to RTSP stream")
        print("=" * 70)
        print()
        print("The server is working. You can use collect_via_server.py")
        sys.exit(0)
    else:
        print("   ⚠️  No data received from stream")
        print("   Server might be having connection issues")
        sys.exit(1)
        
except requests.exceptions.ReadTimeout:
    print("   ❌ Connection timeout!")
    print()
    print("=" * 70)
    print("❌ PROBLEM: Server cannot connect to RTSP stream")
    print("=" * 70)
    print()
    print("The Flask server is having the same 'Operation not permitted' issue.")
    print("The server's ffmpeg process is being blocked by macOS.")
    print()
    print("Solutions:")
    print("  1. Restart Flask server in Terminal (might have different permissions)")
    print("  2. Check macOS System Preferences → Security & Privacy")
    print("     - Grant network access to Python/ffmpeg")
    print("  3. Try running Flask server from Terminal (not automated)")
    print("  4. Check if browser viewer actually works (might be cached)")
    print()
    sys.exit(1)
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
