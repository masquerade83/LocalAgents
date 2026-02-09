#!/bin/bash
# Test RTSP Stream Connection

RTSP_URL="rtsp://kush.sood:admin@123@192.168.29.221/stream1"
IP="192.168.29.221"

echo "RTSP Stream Connection Test"
echo "============================"
echo ""

# Test 1: Network connectivity
echo "1. Testing network connectivity to $IP..."
if ping -c 2 -W 2000 "$IP" > /dev/null 2>&1; then
    echo "   ✅ IP address is reachable"
else
    echo "   ❌ IP address is not reachable"
    echo "   (This might be normal if camera is on a different network)"
fi
echo ""

# Test 2: RTSP port check
echo "2. Testing RTSP port (554)..."
if nc -z -w 2 "$IP" 554 2>/dev/null; then
    echo "   ✅ RTSP port 554 is open"
else
    echo "   ⚠️  Cannot connect to port 554"
    echo "   (Port might be blocked or camera uses different port)"
fi
echo ""

# Test 3: FFmpeg connection test
echo "3. Testing RTSP stream connection..."
echo "   URL: $RTSP_URL"
echo ""

timeout 10 ffmpeg -rtsp_transport tcp -i "$RTSP_URL" -t 2 -f null - 2>&1 | head -20

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo "   ✅ Stream connection successful!"
else
    echo ""
    echo "   ❌ Stream connection failed"
    echo ""
    echo "   Possible issues:"
    echo "   - Camera not accessible from this network"
    echo "   - Incorrect credentials"
    echo "   - URL format issue (password contains @ symbol)"
    echo ""
    echo "   Try URL-encoded version:"
    echo "   rtsp://kush.sood:admin%40123@192.168.29.221/stream1"
fi
