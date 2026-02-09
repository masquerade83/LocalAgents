#!/usr/bin/env python3
"""
Validate that the stream and tunnel work: test-frame (single JPEG) and optionally MJPEG.
Run with: python3 validate_stream_tunnel.py [BASE_URL]
Example: python3 validate_stream_tunnel.py https://your-subdomain.ngrok-free.app
If BASE_URL is omitted, uses http://localhost:5001
"""
import sys
import urllib.request
import urllib.parse

def main():
    base = (sys.argv[1] or "http://localhost:5001").rstrip("/")
    headers = {"ngrok-skip-browser-warning": "true"}
    
    print("1. Testing test-frame (single JPEG)...")
    req = urllib.request.Request(f"{base}/api/stream/test-frame", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            ct = r.headers.get("Content-Type", "")
            data = r.read()
            print(f"   Status: {r.status}, Content-Type: {ct}, Size: {len(data)} bytes")
            if "image" in ct and len(data) > 100:
                print("   OK - test-frame returns an image.")
            else:
                print("   WARN - response may not be an image.")
    except Exception as e:
        print(f"   FAIL: {e}")
        return 1
    
    print("\n2. Testing MJPEG stream (first chunk only)...")
    stream_url = f"{base}/api/stream/mjpeg?url={urllib.parse.quote('rtsp://test')}&yolo=false&confidence=0.25"
    req = urllib.request.Request(stream_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            ct = r.headers.get("Content-Type", "")
            chunk = r.read(4096)
            print(f"   Content-Type: {ct}, First chunk: {len(chunk)} bytes")
            if "multipart" in ct:
                print("   OK - MJPEG endpoint returns multipart.")
            elif "text/html" in ct:
                print("   FAIL - Ngrok returned HTML (interstitial). Use ngrok-skip-browser-warning header in browser.")
            else:
                print(f"   WARN - Unexpected type. First 80 bytes: {chunk[:80]!r}")
    except urllib.error.HTTPError as e:
        print(f"   Expected 400 for invalid RTSP URL: {e.code}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\nDone. If test-frame OK but video still black in browser, add ?debug=1 to the page URL and check console for 'MJPEG frame' logs.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
