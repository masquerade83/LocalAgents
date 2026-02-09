# Final Solution for RTSP Frame Collection

## The Core Problem

macOS is blocking **all** ffmpeg network access with "Operation not permitted". This affects:
- Direct ffmpeg commands
- Flask server's ffmpeg processes
- Any tool using ffmpeg for RTSP

## Why Browser Viewer "Works"

If the browser viewer appears to work, it might be:
1. Showing cached/old frames
2. The server WAS working before but now isn't
3. Using a different connection method

## Solution: Test Server Connection First

Before trying to collect frames, test if the server can actually connect:

```bash
cd /Users/shailja/clawd/object_detection_working/training
python3 test_server_connection.py
```

This will tell you if the server has the same permission issue.

## If Server Can't Connect

### Option 1: Restart Server in Terminal

The server might need to be started from Terminal (not automated) to get proper permissions:

```bash
# Stop any running server
# Then start it in Terminal:
cd /Users/shailja/clawd/object_detection_working
python3 server_yolo.py
```

### Option 2: Grant macOS Permissions

1. **System Preferences** → **Security & Privacy** → **Privacy**
2. Check **Full Disk Access** - add Terminal/Python if needed
3. Check for any permission prompts when running ffmpeg
4. Try running the server once to trigger permission dialogs

### Option 3: Use Alternative Collection Method

If ffmpeg is completely blocked, we can:
1. Use screen recording of the browser viewer
2. Use a different RTSP client library (not ffmpeg-based)
3. Set up a proxy/bridge on a different machine

## If Server CAN Connect

If `test_server_connection.py` shows the server works:

```bash
python3 collect_via_server.py
```

This should work now.

## Quick Diagnostic Commands

```bash
# 1. Test server connection
cd /Users/shailja/clawd/object_detection_working/training
python3 test_server_connection.py

# 2. If server works, collect frames
python3 collect_via_server.py

# 3. If server doesn't work, check macOS permissions
# Then restart server in Terminal and test again
```

## Expected Behavior

- ✅ **Server test passes** → Use `collect_via_server.py`
- ❌ **Server test fails** → Fix macOS permissions, restart server, test again
