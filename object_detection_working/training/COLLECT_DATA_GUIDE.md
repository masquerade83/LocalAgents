# Data Collection Guide

## Issue: "Operation not permitted" Error

If you get this error even when running manually, it's likely a **macOS network permission** issue blocking ffmpeg.

**The stream works in your browser viewer**, which means the connection is fine - macOS is just blocking ffmpeg.

## Quick Solutions

### Option A: Use the Working Server Method (RECOMMENDED)

Since your browser viewer works, use the Flask server to collect frames:

```bash
# 1. Start the Flask server (in one terminal)
cd /Users/shailja/clawd/object_detection_working
python3 server_yolo.py

# 2. Collect frames (in another terminal)
cd /Users/shailja/clawd/object_detection_working/training
python3 collect_via_server.py
```

This uses the same connection method that works in your browser!

### Option B: Fix macOS Permissions

1. Check **System Preferences** → **Security & Privacy** → **Privacy** → **Full Disk Access**
2. Make sure **Terminal** has access
3. When running ffmpeg, macOS might prompt - click **Allow**

### Option C: Use URL-Encoded Password

The password `admin@123` needs URL encoding. Use:
```bash
rtsp://kush.sood:admin%40123@192.168.29.221/stream1
```
(`@` becomes `%40`)

## Solution: Run Manually in Terminal

**IMPORTANT:** The "Operation not permitted" error means you MUST run these commands in your own terminal, not through automated tools.

### Option 1: Use Simple Shell Script (EASIEST)

Open your terminal and run:

```bash
cd /Users/shailja/clawd/object_detection_working/training
./collect_simple.sh
```

This is the simplest method - just run the script in your terminal.

### Option 2: Get the Exact Command

```bash
cd /Users/shailja/clawd/object_detection_working/training
python3 get_collection_command.py
```

This will print the exact command for you to copy-paste.

### Option 3: Run Python Script in Terminal

```bash
cd /Users/shailja/clawd/object_detection_working/training
python3 collect_data.py
```

This will work because your terminal has proper network permissions.

### Option 3: Use ffmpeg Directly

Run this command in your terminal:

```bash
cd /Users/shailja/clawd/object_detection_working/training
mkdir -p dataset/images

ffmpeg \
    -rtsp_transport tcp \
    -i "rtsp://kush.sood:admin@123@192.168.29.221/stream1" \
    -vf "fps=1/2" \
    -frames:v 100 \
    -f image2 \
    -q:v 2 \
    dataset/images/frame_%06d.jpg
```

**Parameters:**
- `fps=1/2` - Capture 1 frame every 2 seconds
- `-frames:v 100` - Capture 100 frames total
- `-q:v 2` - High quality (lower number = better quality, 1-31 range)

## Quick Collection Examples

### Collect 50 frames (1 every 5 seconds)
```bash
ffmpeg -rtsp_transport tcp -i "rtsp://kush.sood:admin@123@192.168.29.221/stream1" \
    -vf "fps=1/5" -frames:v 50 -f image2 -q:v 2 \
    dataset/images/frame_%06d.jpg
```

### Collect 200 frames (1 every 3 seconds)
```bash
ffmpeg -rtsp_transport tcp -i "rtsp://kush.sood:admin@123@192.168.29.221/stream1" \
    -vf "fps=1/3" -frames:v 200 -f image2 -q:v 2 \
    dataset/images/frame_%06d.jpg
```

### Collect frames for 5 minutes (1 per second)
```bash
ffmpeg -rtsp_transport tcp -i "rtsp://kush.sood:admin@123@192.168.29.221/stream1" \
    -vf "fps=1" -t 300 -f image2 -q:v 2 \
    dataset/images/frame_%06d.jpg
```

## After Collection

Once you have frames:

1. **Split dataset:**
   ```bash
   python3 split_dataset.py
   ```

2. **Annotate images** using LabelImg

3. **Train model:**
   ```bash
   python3 train_custom_model.py
   ```

## Tips

- **Start small**: Collect 50-100 frames first to test
- **Diversity**: Capture at different times/conditions
- **Quality**: Use `-q:v 2` for high quality (good for training)
- **Time**: Collection time = MAX_FRAMES × FRAME_INTERVAL
  - Example: 100 frames × 2 seconds = ~3.3 minutes
