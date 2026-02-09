#!/bin/bash
# Start ngrok tunnel to Flask server (port 5001) for Public Base URL (WhatsApp images).
# Prerequisites: Flask server running (./start_yolo.sh or python3 server_yolo.py), ngrok installed and authtoken set.

PORT=5001

if ! command -v ngrok &>/dev/null; then
    echo "ngrok not found. Install it first:"
    echo "  macOS:   brew install ngrok"
    echo "  Other:   https://ngrok.com/download"
    echo "Then:     ngrok config add-authtoken YOUR_TOKEN"
    exit 1
fi

echo "Starting tunnel to http://localhost:$PORT"
echo "Make sure the Flask server is running (e.g. python3 server_yolo.py)."
echo ""
echo "Copy the HTTPS URL below into Dashboard → Alert message & options → Public base URL"
echo "Example: https://abc123.ngrok-free.app (no trailing slash)"
echo ""
ngrok http "$PORT"
