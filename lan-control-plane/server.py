#!/usr/bin/env python3
"""LAN Control Plane — discovery API + Control Plane UI shell."""

from __future__ import annotations

import threading
from typing import Any

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from discovery import scan_network
from registry import merge_registry, upsert_device

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

_lock = threading.Lock()
_last_scan: dict[str, Any] | None = None
_scanning = False


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "lan-control-plane"})


@app.get("/api/devices")
def devices():
    with _lock:
        scan = _last_scan
        scanning = _scanning
    if not scan:
        return jsonify(
            {
                "scanned_at": None,
                "count": 0,
                "devices": [],
                "scanning": scanning,
                "message": "No scan yet. POST /api/scan to discover devices.",
            }
        )
    payload = dict(scan)
    payload["devices"] = merge_registry(scan["devices"])
    payload["scanning"] = scanning
    return jsonify(payload)


@app.post("/api/scan")
def scan():
    global _last_scan, _scanning
    body = request.get_json(silent=True) or {}
    ping_sweep = body.get("ping_sweep", True)

    with _lock:
        if _scanning:
            return jsonify({"ok": False, "error": "scan already in progress"}), 409
        _scanning = True

    try:
        result = scan_network(ping_sweep=bool(ping_sweep))
        result["devices"] = merge_registry(result["devices"])
        with _lock:
            _last_scan = result
        return jsonify(result)
    finally:
        with _lock:
            _scanning = False


@app.patch("/api/devices/<key>")
def patch_device(key: str):
    body = request.get_json(silent=True) or {}
    allowed = {"nickname", "room", "tags", "capabilities", "links"}
    patch = {k: body[k] for k in allowed if k in body}
    if not patch:
        return jsonify({"ok": False, "error": "no allowed fields"}), 400
    saved = upsert_device(key, patch)
    return jsonify({"ok": True, "key": key, "registry": saved})


@app.get("/")
def index():
    return send_from_directory(".", "index.html")


if __name__ == "__main__":
    print("LAN Control Plane → http://127.0.0.1:8765")
    app.run(host="127.0.0.1", port=8765, debug=False)
