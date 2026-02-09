# RTSP URL Fix: Password with @ Symbol

## Problem

The password `admin@123` contains the `@` symbol, which conflicts with RTSP URL format:
```
rtsp://username:password@host/path
```

When ffmpeg sees `rtsp://kush.sood:admin@123@192.168.29.221/stream1`, it gets confused because:
- The first `@` might be interpreted as the separator
- It could parse as: username=`kush.sood`, password=`admin`, host=`123@192.168.29.221` (WRONG!)

## Solution: URL Encoding

URL-encode the `@` symbol in the password:
- `@` → `%40`
- `admin@123` → `admin%40123`

## Corrected URLs

### For Python scripts:
```python
RTSP_URL = 'rtsp://kush.sood:admin%40123@192.168.29.221/stream1'
```

### For shell scripts:
```bash
RTSP_URL="rtsp://kush.sood:admin%40123@192.168.29.221/stream1"
```

### For direct ffmpeg command:
```bash
ffmpeg -rtsp_transport tcp -i "rtsp://kush.sood:admin%40123@192.168.29.221/stream1" ...
```

## Testing

Run the diagnostic script to find the working format:
```bash
python3 diagnose_rtsp.py
```

Or try the collection script with encoded URL:
```bash
./collect_with_encoded_url.sh
```

## Alternative: Use Environment Variable

If you want to avoid hardcoding:
```bash
export RTSP_URL="rtsp://kush.sood:admin%40123@192.168.29.221/stream1"
ffmpeg -rtsp_transport tcp -i "$RTSP_URL" ...
```
