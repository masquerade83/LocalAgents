#!/usr/bin/env python3
"""Local web UI to start/stop the Hermes stack. Binds 127.0.0.1 only."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
STACKCTL = ROOT / "stackctl.sh"
OBSERVE = ROOT.parent / "observability" / "stack_observe.py"
PORT = int(os.environ.get("HERMES_SWITCH_PORT", os.environ.get("STACK_CONTROL_PORT", "9120")))
HOST = "127.0.0.1"

LABELS = {
    "ollama": {"title": "Ollama", "subtitle": "Local LLM backend", "port": 11434, "url": "http://127.0.0.1:11434"},
    "postgres": {"title": "LiteLLM Postgres", "subtitle": "Model config store", "port": 5432},
    "litellm": {"title": "LiteLLM", "subtitle": "OpenAI proxy", "port": 4000, "url": "http://127.0.0.1:4000/ui"},
    "router": {"title": "Model Router", "subtitle": "Content-aware routing", "port": 3999, "url": "http://127.0.0.1:3999/health"},
    "gateway": {"title": "Hermes Gateway", "subtitle": "Telegram @DhauladharBot", "port": None},
    "n8n": {"title": "n8n", "subtitle": "Workflow automation", "port": 5678, "url": "http://127.0.0.1:5678"},
    "prometheus": {"title": "Prometheus", "subtitle": "Metrics TSDB", "port": 9090, "url": "http://127.0.0.1:9090"},
    "grafana": {"title": "Grafana", "subtitle": "Stack dashboards", "port": 3000, "url": "http://127.0.0.1:3000"},
    "ollama_exporter": {"title": "Ollama VRAM exporter", "subtitle": "Prometheus :9101", "port": 9101, "url": "http://127.0.0.1:9101/metrics"},
    "ollama_inference_proxy": {"title": "Ollama inference proxy", "subtitle": "Prefill/decode metrics :11435→11434", "port": 11435, "url": "http://127.0.0.1:9102/metrics"},
}


def run_stackctl(action: str, target: str = "all") -> tuple[int, str]:
    cmd = [str(STACKCTL), action]
    if target:
        cmd.append(target)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def get_status() -> list[dict]:
    proc = subprocess.run([str(STACKCTL), "status"], capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "status failed")
    rows = json.loads(proc.stdout)
    for row in rows:
        meta = LABELS.get(row["name"], {})
        row.update(meta)
    return rows


def get_observe() -> dict:
    if not OBSERVE.is_file():
        raise RuntimeError(f"missing {OBSERVE}")
    proc = subprocess.run(
        [sys.executable, str(OBSERVE)],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "observe failed")
    return json.loads(proc.stdout)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._file(ROOT / "index.html", "text/html; charset=utf-8")
        if path == "/api/observe":
            try:
                return self._json(200, {"ok": True, **get_observe()})
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})
        if path == "/api/status":
            try:
                return self._json(200, {"ok": True, "services": get_status()})
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        qs = parse_qs(urlparse(self.path).query)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        action = data.get("action") or qs.get("action", [None])[0]
        service = data.get("service") or qs.get("service", ["all"])[0]

        if path == "/api/action" and action in ("start", "stop"):
            code, output = run_stackctl(action, service)
            try:
                services = get_status()
            except Exception as e:
                services = []
                output += f"\nstatus error: {e}"
            return self._json(200 if code == 0 else 500, {
                "ok": code == 0,
                "action": action,
                "service": service,
                "output": output,
                "services": services,
            })

        self.send_error(HTTPStatus.NOT_FOUND)


def main() -> None:
    if not STACKCTL.is_file():
        sys.exit(f"missing {STACKCTL}")
    os.chmod(STACKCTL, 0o755)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Hermes Switch → http://{HOST}:{PORT}")
    print("Ctrl+C to stop this panel (does not stop the stack)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down panel")


if __name__ == "__main__":
    main()
