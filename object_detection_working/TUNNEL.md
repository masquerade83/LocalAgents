# Tunnel setup (Public Base URL for WhatsApp images)

Twilio needs a **public URL** to fetch the alert frame image. This guide sets up a tunnel so your local Flask server is reachable from the internet.

## Option 1: ngrok (recommended)

ngrok gives you a stable HTTPS URL (e.g. `https://abc123.ngrok-free.app`) that forwards to your local server.

### 1. Install ngrok

- **macOS:** `brew install ngrok`
- **Windows:** Download from [ngrok.com/download](https://ngrok.com/download) or Windows Store
- **Linux:** See [ngrok.com/download](https://ngrok.com/download)

### 2. Sign up and add auth token

1. Create a free account at [ngrok.com](https://ngrok.com)
2. In the dashboard, copy your **authtoken**
3. Run once:
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

### 3. Start the tunnel

**Start your Flask server first** (in one terminal):

```bash
cd object_detection_working
python3 server_yolo.py
```

**Then start the tunnel** (in another terminal):

```bash
cd object_detection_working
./run_tunnel.sh
```

Or manually:

```bash
ngrok http 5001
```

(Use `5001` because `server_yolo.py` runs on port 5001 by default.)

### 4. Copy the public URL

ngrok will show something like:

```
Forwarding   https://a1b2c3d4.ngrok-free.app -> http://localhost:5001
```

Copy the **https** URL (e.g. `https://a1b2c3d4.ngrok-free.app`) — **no trailing slash**.

### 5. Set it in the dashboard

1. Open the **Analytics dashboard** → **Alert message & options**
2. Paste the URL into **Public base URL** (e.g. `https://a1b2c3d4.ngrok-free.app`)
3. Check **Attach current frame to WhatsApp** if you want images
4. Click **Save alert config**

Twilio will then fetch images from `https://your-ngrok-url.ngrok-free.app/api/analytics/alert-frame`.

---

## Option 2: localtunnel (no signup)

If you don’t want to sign up for ngrok:

```bash
npx localtunnel --port 5001
```

Use the printed URL (e.g. `https://something.loca.lt`) as **Public base URL**. The URL changes each time you run it.

---

## Notes

- **Free ngrok:** The URL changes each time you restart ngrok unless you have a paid plan. After restarting, update **Public base URL** in the dashboard.
- **Keep tunnel running:** Leave the tunnel process running while you want WhatsApp images to work.
- **Port:** If you changed the Flask port in `server_yolo.py`, use that port in the tunnel command (e.g. `ngrok http 8080`).
- **Browser stream:** The live RTSP viewer may show a black screen when opened via the tunnel URL; WhatsApp alert images still work. Use the viewer on localhost when you need to see the live feed. (To debug the tunnel viewer later: see `app.js` fetch/MJPEG path and `?debug=1`.)
