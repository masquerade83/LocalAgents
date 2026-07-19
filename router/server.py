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
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from rules import pick_model, should_strip_tools

HOST = os.environ.get("HERMES_ROUTER_HOST", "0.0.0.0")
PORT = int(os.environ.get("HERMES_ROUTER_PORT", "3999"))
UPSTREAM = os.environ.get("LITELLM_UPSTREAM", "http://127.0.0.1:4000").rstrip("/")
MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "admin")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [router] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("hermes-router")


def _proxy(method: str, path: str, body: bytes | None, extra_headers: dict[str, str] | None = None) -> tuple[int, bytes, dict[str, str]]:
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
    server_version = "HermesModelRouter/1.0"

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
        if self.path in ("/", "/"):
            info = {
                "service": "hermes-model-router",
                "upstream": UPSTREAM,
                "endpoints": ["/health", "/v1/models", "/v1/chat/completions"],
            }
            return self._send(200, json.dumps(info, indent=2).encode())

        if self.path.startswith("/v1/"):
            code, data, _ = _proxy("GET", self.path, None)
            return self._send(code, data)

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"

        if self.path != "/v1/chat/completions":
            code, data, _ = _proxy("POST", self.path, raw)
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

        if should_strip_tools(chosen):
            stripped = [k for k in ("tools", "tool_choice", "parallel_tool_calls") if payload.pop(k, None)]
            if stripped:
                log.info("stripped %s for non-agentic model %s (%s)", ",".join(stripped), chosen, reason)
        else:
            log.info("route in=%s out=%s reason=%s tools=kept", requested, chosen, reason)

        t0 = time.perf_counter()
        out_body = json.dumps(payload).encode("utf-8")
        code, data, _ = _proxy("POST", self.path, out_body)
        ms = (time.perf_counter() - t0) * 1000
        log.info(
            "route in=%s out=%s reason=%s status=%s %.0fms has_image=%s",
            requested,
            chosen,
            reason,
            code,
            ms,
            any(
                isinstance(m.get("content"), list)
                and any(isinstance(b, dict) and b.get("type") == "image_url" for b in m["content"])
                for m in messages
                if isinstance(m, dict)
            ),
        )
        return self._send(code, data)


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    log.info("listening on http://%s:%s → %s", HOST, PORT, UPSTREAM)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("shutdown")
        sys.exit(0)


if __name__ == "__main__":
    main()
