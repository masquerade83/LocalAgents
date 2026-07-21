#!/usr/bin/env python3
"""Transparent Ollama HTTP proxy with Prometheus prefill/decode/TTFT/ITL metrics.

LiteLLM → this proxy (:11435) → Ollama (:11434)
Scrape metrics at :9102/metrics

Jupyter-learning and direct `ollama` CLI should keep using :11434.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
except ImportError:
    print("Install prometheus_client: pip install prometheus_client", file=sys.stderr)
    sys.exit(1)

UPSTREAM = os.environ.get("OLLAMA_UPSTREAM", "http://127.0.0.1:11434").rstrip("/")
PROXY_HOST = os.environ.get("OLLAMA_PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(os.environ.get("OLLAMA_PROXY_PORT", "11435"))
METRICS_HOST = os.environ.get("OLLAMA_INFERENCE_METRICS_HOST", "127.0.0.1")
METRICS_PORT = int(os.environ.get("OLLAMA_INFERENCE_METRICS_PORT", "9102"))

LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60, 120, 300)
ITL_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)

REQUESTS = Counter(
    "ollama_inference_requests_total",
    "Inference requests through the Hermes Ollama proxy",
    ["model", "route", "stream"],
)
PREFILL = Histogram(
    "ollama_prefill_seconds",
    "Prompt evaluation (prefill) duration from Ollama prompt_eval_duration",
    ["model"],
    buckets=LATENCY_BUCKETS,
)
DECODE = Histogram(
    "ollama_decode_seconds",
    "Token generation (decode) duration from Ollama eval_duration",
    ["model"],
    buckets=LATENCY_BUCKETS,
)
TTFT = Histogram(
    "ollama_ttft_seconds",
    "Time from request start to first streamed token chunk",
    ["model"],
    buckets=LATENCY_BUCKETS,
)
ITL = Histogram(
    "ollama_itl_seconds",
    "Inter-token latency (eval_duration / eval_count)",
    ["model"],
    buckets=ITL_BUCKETS,
)
TOKENS_OUT = Counter("ollama_output_tokens_total", "Output tokens (eval_count)", ["model"])
TOKENS_IN = Counter("ollama_prompt_tokens_total", "Prompt tokens (prompt_eval_count)", ["model"])


def _model_from_payload(payload: dict[str, Any]) -> str:
    return str(payload.get("model") or payload.get("name") or "unknown")


def _record_ollama_timings(model: str, data: dict[str, Any], *, ttft_s: float | None) -> None:
    if ttft_s is not None:
        TTFT.labels(model=model).observe(ttft_s)

    prompt_ns = data.get("prompt_eval_duration")
    eval_ns = data.get("eval_duration")
    eval_count = data.get("eval_count") or 0
    prompt_count = data.get("prompt_eval_count") or 0

    if prompt_ns:
        PREFILL.labels(model=model).observe(int(prompt_ns) / 1e9)
    if eval_ns:
        DECODE.labels(model=model).observe(int(eval_ns) / 1e9)
    if eval_count:
        TOKENS_OUT.labels(model=model).inc(int(eval_count))
        if eval_ns:
            ITL.labels(model=model).observe(int(eval_ns) / 1e9 / int(eval_count))
    if prompt_count:
        TOKENS_IN.labels(model=model).inc(int(prompt_count))


def _parse_stream_line(line: bytes) -> dict[str, Any] | None:
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


class MetricsHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        pass

    def do_GET(self) -> None:
        if self.path != "/metrics":
            self.send_error(404)
            return
        body = generate_latest()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE_LATEST)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        pass

    def _forward_simple(self, method: str) -> None:
        url = f"{UPSTREAM}{self.path}"
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length")}
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = resp.read()
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            err_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)

    def _forward_inference(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            payload = {}
        model = _model_from_payload(payload)
        stream = bool(payload.get("stream", False))
        route = self.path.split("?", 1)[0]
        REQUESTS.labels(model=model, route=route, stream=str(stream).lower()).inc()

        url = f"{UPSTREAM}{self.path}"
        headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length")}
        req = urllib.request.Request(url, data=raw, method="POST", headers=headers)

        t0 = time.perf_counter()
        ttft_recorded = False
        ttft_s: float | None = None
        final: dict[str, Any] | None = None

        try:
            resp = urllib.request.urlopen(req, timeout=600)
        except urllib.error.HTTPError as e:
            err_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)
            return

        self.send_response(resp.status)
        for k, v in resp.headers.items():
            if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                self.send_header(k, v)
        self.end_headers()

        if stream:
            buffer = b""
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    data = _parse_stream_line(line)
                    if not data:
                        continue
                    if not ttft_recorded:
                        msg = data.get("message") or {}
                        token = data.get("response") or msg.get("content")
                        if token:
                            ttft_s = time.perf_counter() - t0
                            ttft_recorded = True
                    if data.get("done"):
                        final = data
            if buffer.strip():
                data = _parse_stream_line(buffer)
                if data and data.get("done"):
                    final = data
        else:
            data = resp.read()
            self.wfile.write(data)
            try:
                final = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                final = None

        if final:
            _record_ollama_timings(model, final, ttft_s=ttft_s)

    def do_GET(self) -> None:
        self._forward_simple("GET")

    def do_POST(self) -> None:
        if self.path.startswith(("/api/chat", "/api/generate", "/v1/chat/completions", "/v1/completions")):
            return self._forward_inference()
        self._forward_simple("POST")


def main() -> None:
    metrics_httpd = ThreadingHTTPServer((METRICS_HOST, METRICS_PORT), MetricsHandler)
    proxy_httpd = ThreadingHTTPServer((PROXY_HOST, PROXY_PORT), ProxyHandler)
    threading.Thread(target=metrics_httpd.serve_forever, daemon=True).start()
    print(
        f"Ollama inference proxy → http://{PROXY_HOST}:{PROXY_PORT} → {UPSTREAM}\n"
        f"Metrics → http://{METRICS_HOST}:{METRICS_PORT}/metrics",
        flush=True,
    )
    try:
        proxy_httpd.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
