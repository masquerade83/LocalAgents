#!/usr/bin/env python3
"""OpenAI-compatible model router: content-aware selection → LiteLLM upstream."""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from rules import pick_model, should_strip_tools

# Observability helpers (repo-relative import path when run from router/)
_OBS = Path(__file__).resolve().parent.parent / "observability"
if str(_OBS) not in sys.path:
    sys.path.insert(0, str(_OBS.parent))
from observability.metrics import RouterMetrics
from observability.trace_context import extract_or_create, trace_record

HOST = os.environ.get("HERMES_ROUTER_HOST", "0.0.0.0")
PORT = int(os.environ.get("HERMES_ROUTER_PORT", "3999"))
UPSTREAM = os.environ.get("LITELLM_UPSTREAM", "http://127.0.0.1:4000").rstrip("/")
MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "admin")
LOG_DIR = Path(os.environ.get("HERMES_LOG_DIR", Path.home() / ".hermes" / "logs"))
DECISIONS_LOG = LOG_DIR / "decisions.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [router] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("hermes-router")
METRICS = RouterMetrics()


def _ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _write_decision(record: dict[str, Any]) -> None:
    try:
        _ensure_log_dir()
        with DECISIONS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as e:
        log.warning("decisions.jsonl write failed: %s", e)


def _has_image(messages: list[Any]) -> bool:
    for m in messages:
        if not isinstance(m, dict):
            continue
        content = m.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "image_url":
                    return True
    return False


def _proxy(
    method: str,
    path: str,
    body: bytes | None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, bytes, dict[str, str]]:
    url = f"{UPSTREAM}{path}"
    headers = {
        "Authorization": f"Bearer {MASTER_KEY}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = resp.read()
            return resp.status, data, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


class Handler(BaseHTTPRequestHandler):
    server_version = "HermesModelRouter/1.1"

    def log_message(self, fmt: str, *args) -> None:
        log.info("%s - %s", self.address_string(), fmt % args)

    def _send(self, code: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/health", "/healthz"):
            return self._send(200, b'{"ok":true,"service":"hermes-router"}\n')
        if self.path == "/metrics":
            body = METRICS.render_prometheus().encode()
            return self._send(200, body, "text/plain; version=0.0.4; charset=utf-8")
        if self.path in ("/", "/"):
            info = {
                "service": "hermes-model-router",
                "upstream": UPSTREAM,
                "endpoints": ["/health", "/metrics", "/v1/models", "/v1/chat/completions"],
            }
            return self._send(200, json.dumps(info, indent=2).encode())

        if self.path.startswith("/v1/"):
            code, data, _ = _proxy("GET", self.path, None)
            return self._send(code, data)

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        inbound_headers = {k: v for k, v in self.headers.items()}
        request_id, traceparent, propagate = extract_or_create(inbound_headers)

        if self.path != "/v1/chat/completions":
            code, data, _ = _proxy("POST", self.path, raw, propagate)
            return self._send(code, data)

        try:
            payload: dict[str, Any] = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST, "invalid json")
            return

        requested = payload.get("model")
        messages = payload.get("messages") or []
        has_tools = bool(payload.get("tools"))
        chosen, reason = pick_model(requested, messages, has_tools=has_tools)
        payload["model"] = chosen
        has_image = _has_image(messages)

        if should_strip_tools(chosen):
            stripped = [k for k in ("tools", "tool_choice", "parallel_tool_calls") if payload.pop(k, None)]
            if stripped:
                log.info(
                    "request_id=%s stripped %s for non-agentic model %s (%s)",
                    request_id,
                    ",".join(stripped),
                    chosen,
                    reason,
                )
        else:
            log.info("request_id=%s route in=%s out=%s reason=%s tools=kept", request_id, requested, chosen, reason)

        t0 = time.perf_counter()
        out_body = json.dumps(payload).encode("utf-8")
        code, data, _ = _proxy("POST", self.path, out_body, propagate)
        ms = (time.perf_counter() - t0) * 1000
        status = code

        log.info(
            "request_id=%s route in=%s out=%s reason=%s status=%s %.0fms has_image=%s trace=%s",
            request_id,
            requested,
            chosen,
            reason,
            status,
            ms,
            has_image,
            traceparent,
        )

        METRICS.record_request(out_model=str(chosen), reason=str(reason), status=status, latency_ms=ms)

        decision = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            **trace_record(
                request_id,
                traceparent,
                extra={
                    "in_model": requested,
                    "out_model": chosen,
                    "reason": reason,
                    "latency_ms": round(ms, 1),
                    "has_image": has_image,
                    "status": status,
                },
            ),
        }
        _write_decision(decision)

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Request-ID", request_id)
        self.send_header("traceparent", traceparent)
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    _ensure_log_dir()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    log.info("listening on http://%s:%s → %s (decisions → %s)", HOST, PORT, UPSTREAM, DECISIONS_LOG)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("shutdown")
        sys.exit(0)


if __name__ == "__main__":
    main()
