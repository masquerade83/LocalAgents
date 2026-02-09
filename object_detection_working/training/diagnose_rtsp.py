#!/usr/bin/env python3
"""
Diagnostic script for RTSP connection issues
Tests different URL formats and connection methods
"""

import subprocess
import urllib.parse
import sys

# Original URL
RTSP_URL = 'rtsp://kush.sood:admin@123@192.168.29.221/stream1'

print("=" * 70)
print("RTSP Connection Diagnostic Tool")
print("=" * 70)
print()

# Parse the URL to understand the issue
print("1. Analyzing RTSP URL...")
print(f"   Original URL: {RTSP_URL}")
print()

# The issue: password contains @ symbol
# RTSP format: rtsp://username:password@host:port/path
# With password "admin@123", it becomes ambiguous

# Try different URL formats
url_variants = []

# Option 1: URL encode the password
username = "kush.sood"
password = "admin@123"
host = "192.168.29.221"
path = "/stream1"

# URL encode the password
encoded_password = urllib.parse.quote(password, safe='')
url_encoded = f"rtsp://{username}:{encoded_password}@{host}{path}"
url_variants.append(("URL-encoded password", url_encoded))

# Option 2: Try with quotes (for shell)
url_quoted = f'rtsp://{username}:{password}@{host}{path}'
url_variants.append(("Quoted URL (for shell)", url_quoted))

# Option 3: Try without password encoding (original)
url_variants.append(("Original URL", RTSP_URL))

# Option 4: Try with different RTSP transport
url_variants.append(("With UDP transport", RTSP_URL))

print("2. Testing different URL formats...")
print()

for i, (name, url) in enumerate(url_variants, 1):
    print(f"   Test {i}: {name}")
    print(f"   URL: {url}")
    
    # Test with ffprobe first (lighter than ffmpeg)
    cmd_probe = [
        'ffprobe',
        '-rtsp_transport', 'tcp',
        '-i', url,
        '-v', 'error',
        '-show_entries', 'stream=codec_name',
        '-of', 'default=noprint_wrappers=1:nokey=1'
    ]
    
    try:
        result = subprocess.run(
            cmd_probe,
            capture_output=True,
            timeout=5,
            text=True
        )
        
        if result.returncode == 0:
            print(f"   ✅ SUCCESS! Stream is accessible")
            print(f"   Codec: {result.stdout.strip()}")
            print()
            print("=" * 70)
            print(f"✅ WORKING URL: {url}")
            print("=" * 70)
            print()
            print("Use this URL in your collection script:")
            print(f'RTSP_URL = "{url}"')
            print()
            sys.exit(0)
        else:
            error_msg = result.stderr[-200:] if result.stderr else "Unknown error"
            print(f"   ❌ Failed: {error_msg.strip()}")
    except subprocess.TimeoutExpired:
        print(f"   ⚠️  Timeout (stream might be slow or unreachable)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()

# If all failed, try UDP
print("3. Testing UDP transport (if TCP failed)...")
print()

for name, url in url_variants[:3]:  # Test first 3 with UDP
    print(f"   Testing: {name} (UDP)")
    cmd_probe = [
        'ffprobe',
        '-rtsp_transport', 'udp',
        '-i', url,
        '-v', 'error',
        '-timeout', '5000000',  # 5 second timeout in microseconds
        '-show_entries', 'stream=codec_name',
        '-of', 'default=noprint_wrappers=1:nokey=1'
    ]
    
    try:
        result = subprocess.run(
            cmd_probe,
            capture_output=True,
            timeout=5,
            text=True
        )
        
        if result.returncode == 0:
            print(f"   ✅ SUCCESS with UDP! Stream is accessible")
            print()
            print("=" * 70)
            print(f"✅ WORKING URL (UDP): {url}")
            print("=" * 70)
            print()
            print("Use this URL with UDP transport:")
            print(f'RTSP_URL = "{url}"')
            print("And use: ffmpeg -rtsp_transport udp ...")
            print()
            sys.exit(0)
    except:
        pass

print()
print("=" * 70)
print("❌ All connection attempts failed")
print("=" * 70)
print()
print("Possible issues:")
print("  1. Network connectivity - can you ping 192.168.29.221?")
print("  2. RTSP stream might be down or changed")
print("  3. Firewall blocking RTSP (port 554)")
print("  4. Authentication credentials might be wrong")
print("  5. macOS network restrictions")
print()
print("Troubleshooting steps:")
print("  1. Test network: ping 192.168.29.221")
print("  2. Test RTSP port: nc -zv 192.168.29.221 554")
print("  3. Try VLC: vlc rtsp://kush.sood:admin@123@192.168.29.221/stream1")
print("  4. Check if stream works in browser viewer")
print()
