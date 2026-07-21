#!/usr/bin/env python3
"""Prometheus exporter for Ollama VRAM — polls /api/ps, exposes /metrics on :9101."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
HOST = os.environ.get("OLLAMA_EXPORTER_HOST", "127.0.0.1")
PORT = int(os.environ.get("OLLAMA_EXPORTER_PORT", "9101"))


def fetch_ps() -> dict | None:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/ps", timeout=3) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def render_metrics(data: dict | None) -> str:
    lines = [
        "# HELP ollama_up Ollama /api/ps reachable.",
        "# TYPE ollama_up gauge",
        f"ollama_up {1 if data else 0}",
    ]
    models = (data or {}).get("models", [])
    total_vram = sum(int(m.get("size_vram", 0)) for m in models)

    lines.extend([
        "# HELP ollama_models_loaded Number of models in VRAM.",
        "# TYPE ollama_models_loaded gauge",
        f"ollama_models_loaded {len(models)}",
        "# HELP ollama_vram_bytes Total VRAM bytes used by loaded models.",
        "# TYPE ollama_vram_bytes gauge",
        f"ollama_vram_bytes {total_vram}",
    ])

    for m in models:
        name = (m.get("name") or "unknown").replace("\\", "\\\\").replace('"', '\\"')
        vram = int(m.get("size_vram", 0))
        ctx = int(m.get("context_length") or 0)
        lines.append(f'ollama_model_vram_bytes{{model="{name}"}} {vram}')
        lines.append(f'ollama_model_context_length{{model="{name}"}} {ctx}')

    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        pass

    def do_GET(self) -> None:
        if self.path not in ("/metrics", "/"):
            self.send_error(404)
            return
        body = render_metrics(fetch_ps()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Ollama VRAM exporter → http://{HOST}:{PORT}/metrics (ollama={OLLAMA_URL})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
