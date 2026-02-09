# RTSP Collection Troubleshooting

## Current Issue: "Operation not permitted"

Even when running manually, you're getting:
```
[rtsp @ ...] Failed reading RTSP data: End of file
Error opening input: Operation not permitted
```

## Why This Happens

The stream **works in your browser viewer**, which means:
- ✅ Network connectivity is fine
- ✅ RTSP stream is accessible
- ✅ Credentials are correct
- ❌ **macOS is blocking ffmpeg from network access**

## Solution 1: Grant Network Permissions to Terminal/ffmpeg

macOS may be blocking network access. Try:

1. **Check System Preferences:**
   - Go to **System Preferences** → **Security & Privacy** → **Privacy** → **Full Disk Access**
   - Make sure **Terminal** (or your terminal app) has access
   - Also check **Network** permissions

2. **Grant permissions when prompted:**
   - When you run ffmpeg, macOS might show a permission dialog
   - Click **Allow** or **Open System Preferences**

3. **Try running with sudo (if needed):**
   ```bash
   sudo ffmpeg -rtsp_transport tcp -i "rtsp://kush.sood:admin%40123@192.168.29.221/stream1" ...
   ```
   (Note: This might not work if it's a network permission issue)

## Solution 2: Use the Working Browser Viewer Method

Since the browser viewer works, we can use the Flask server to collect frames:

```bash
cd /Users/shailja/clawd/object_detection_working
python3 collect_via_server.py
```

This uses the same connection method that works in your browser.

## Solution 3: Test Network Connectivity

Run these in your terminal to verify:

```bash
# Test if you can reach the camera
ping -c 3 192.168.29.221

# Test if RTSP port is open
nc -zv 192.168.29.221 554

# Test with VLC (if installed)
vlc rtsp://kush.sood:admin%40123@192.168.29.221/stream1
```

## Solution 4: Use Python requests (Alternative)

If ffmpeg is blocked, we can use Python's requests library to capture frames from the MJPEG stream that the Flask server creates.

## Solution 5: Check Firewall

```bash
# Check macOS firewall status
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# If firewall is on, you might need to add an exception
```

## Quick Test

Try this minimal test in your terminal:

```bash
cd /Users/shailja/clawd/object_detection_working/training
mkdir -p dataset/images
ffprobe -rtsp_transport tcp -i "rtsp://kush.sood:admin%40123@192.168.29.221/stream1" -v error
```

If this works, then try the full collection command.

## Next Steps

1. First, try **Solution 1** (check macOS permissions)
2. If that doesn't work, try **Solution 2** (use the working server method)
3. Run the network tests from **Solution 3** to verify connectivity
4. If all else fails, we can implement **Solution 4** (Python-based collection)
