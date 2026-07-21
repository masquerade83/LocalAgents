"""W3C Trace Context propagation (traceparent/tracestate) without heavy deps.

Used by the model router to correlate Gateway → Router → LiteLLM requests.
Compatible with OpenTelemetry HTTP propagators.
"""

from __future__ import annotations

import re
import secrets
import uuid
from typing import Any

_TRACEPARENT_RE = re.compile(
    r"^00-(?P<trace_id>[0-9a-f]{32})-(?P<span_id>[0-9a-f]{16})-(?P<flags>[0-9a-f]{2})$",
    re.IGNORECASE,
)


def new_trace_id() -> str:
    return uuid.uuid4().hex


def new_span_id() -> str:
    return secrets.token_hex(8)


def parse_traceparent(value: str | None) -> dict[str, str] | None:
    if not value:
        return None
    m = _TRACEPARENT_RE.match(value.strip())
    if not m:
        return None
    return {
        "trace_id": m.group("trace_id").lower(),
        "span_id": m.group("span_id").lower(),
        "flags": m.group("flags").lower(),
    }


def format_traceparent(trace_id: str, span_id: str, sampled: bool = True) -> str:
    flags = "01" if sampled else "00"
    return f"00-{trace_id}-{span_id}-{flags}"


def extract_or_create(headers: dict[str, str]) -> tuple[str, str, dict[str, str]]:
    """Return (request_id, traceparent, outbound_headers)."""
    # Normalize header keys to lowercase for lookup
    lower = {k.lower(): v for k, v in headers.items()}

    request_id = lower.get("x-request-id") or str(uuid.uuid4())

    parsed = parse_traceparent(lower.get("traceparent"))
    if parsed:
        trace_id = parsed["trace_id"]
        child_span = new_span_id()
    else:
        trace_id = new_trace_id()
        child_span = new_span_id()

    traceparent = format_traceparent(trace_id, child_span)
    outbound = {
        "X-Request-ID": request_id,
        "traceparent": traceparent,
    }
    if "tracestate" in lower:
        outbound["tracestate"] = lower["tracestate"]
    return request_id, traceparent, outbound


def trace_record(
    request_id: str,
    traceparent: str,
    *,
    component: str = "hermes-router",
    span_name: str = "chat_completions",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parsed = parse_traceparent(traceparent)
    rec: dict[str, Any] = {
        "request_id": request_id,
        "traceparent": traceparent,
        "trace_id": parsed["trace_id"] if parsed else None,
        "span_id": parsed["span_id"] if parsed else None,
        "component": component,
        "span_name": span_name,
    }
    if extra:
        rec.update(extra)
    return rec
