# RTSP Stream Viewer

A web-based viewer for RTSP live video streams. Converts RTSP streams to browser-compatible MJPEG format.

## Features

- 🌐 **Web-based** - View RTSP streams in your browser
- 🔄 **Real-time** - Low latency streaming (10 FPS)
- 🎥 **Multiple formats** - Supports various RTSP sources
- 🎨 **Clean UI** - Simple, modern interface
- ⚡ **Easy to use** - Just paste your RTSP URL and connect

## Prerequisites

1. **FFmpeg** - Required for stream conversion
   ```bash
   brew install ffmpeg
   ```

2. **Python Dependencies**
   ```bash
   pip install flask flask-cors
   ```

## Setup

1. **Start the server:**
   ```bash
   cd /Users/shailja/clawd/rtsp-viewer
   python3 server.py
   ```

2. **Open in browser:**
   ```
   http://localhost:5001
   ```

3. **Enter RTSP URL:**
   - Format: `rtsp://username:password@ip:port/stream`
   - Example: `rtsp://admin:password123@192.168.1.100:554/stream1`

4. **Click Connect** to start viewing

## RTSP URL Formats

Common RTSP URL formats:

- **Basic**: `rtsp://ip:port/stream`
- **With auth**: `rtsp://user:pass@ip:port/stream`
- **Hikvision**: `rtsp://user:pass@ip:554/Streaming/Channels/101`
- **Dahua**: `rtsp://user:pass@ip:554/cam/realmonitor?channel=1&subtype=0`
- **Axis**: `rtsp://user:pass@ip/axis-media/media.amp`

## How It Works

1. Backend receives RTSP URL
2. FFmpeg converts RTSP stream to MJPEG
3. MJPEG frames are served via HTTP
4. Browser displays frames in real-time

## Troubleshooting

### Stream won't connect
- Check RTSP URL format
- Verify camera/stream is accessible
- Check network connectivity
- Try using TCP transport: `rtsp://...?tcp`

### Low frame rate
- Adjust FPS in `server.py` (currently 10 FPS)
- Reduce resolution scaling
- Check network bandwidth

### FFmpeg errors
- Make sure ffmpeg is installed: `ffmpeg -version`
- Check RTSP stream is actually accessible
- Some cameras require specific RTSP transport (TCP vs UDP)

## Configuration

Edit `server.py` to customize:

- **Frame rate**: Change `fps=10` to desired FPS
- **Resolution**: Change `scale=1280:-1` to desired width
- **Quality**: Change `-q:v 5` (lower = better quality, 2-31 range)

## Security Notes

- RTSP URLs with passwords are stored in memory only
- Streams are not recorded or saved
- Use HTTPS in production for secure access

## File Structure

```
rtsp-viewer/
├── index.html      # Main UI
├── styles.css      # Styling
├── app.js          # Frontend JavaScript
├── server.py       # Backend Flask server
└── README.md       # This file
```
