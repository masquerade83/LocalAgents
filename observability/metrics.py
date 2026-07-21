"""Minimal Prometheus text exposition for the Hermes router (stdlib only)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any


class RouterMetrics:
    """Thread-safe counters and latency sums for /metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started = time.time()
        self._requests_total: dict[tuple[str, str, str], int] = defaultdict(int)
        self._duration_sum: dict[tuple[str, str], float] = defaultdict(float)
        self._duration_count: dict[tuple[str, str], int] = defaultdict(int)

    def record_request(
        self,
        *,
        out_model: str,
        reason: str,
        status: int,
        latency_ms: float,
    ) -> None:
        status_class = f"{status // 100}xx"
        key = (out_model, reason, status_class)
        dur_key = (out_model, reason)
        with self._lock:
            self._requests_total[key] += 1
            self._duration_sum[dur_key] += latency_ms / 1000.0
            self._duration_count[dur_key] += 1

    def render_prometheus(self) -> str:
        lines: list[str] = []
        uptime = time.time() - self._started
        lines.append("# HELP hermes_router_up Router process is running.")
        lines.append("# TYPE hermes_router_up gauge")
        lines.append("hermes_router_up 1")
        lines.append("# HELP hermes_router_uptime_seconds Seconds since router start.")
        lines.append("# TYPE hermes_router_uptime_seconds gauge")
        lines.append(f"hermes_router_uptime_seconds {uptime:.3f}")

        lines.append("# HELP hermes_router_requests_total Chat completion requests routed.")
        lines.append("# TYPE hermes_router_requests_total counter")
        with self._lock:
            for (model, reason, status_class), count in sorted(self._requests_total.items()):
                rm = _esc(model)
                rr = _esc(reason)
                rs = _esc(status_class)
                lines.append(
                    f'hermes_router_requests_total{{model="{rm}",reason="{rr}",status_class="{rs}"}} {count}'
                )

            lines.append("# HELP hermes_router_request_duration_seconds_sum Cumulative route latency.")
            lines.append("# TYPE hermes_router_request_duration_seconds_sum counter")
            for (model, reason), total in sorted(self._duration_sum.items()):
                lines.append(
                    f'hermes_router_request_duration_seconds_sum{{model="{_esc(model)}",reason="{_esc(reason)}"}} {total:.6f}'
                )

            lines.append("# HELP hermes_router_request_duration_seconds_count Route latency sample count.")
            lines.append("# TYPE hermes_router_request_duration_seconds_count counter")
            for (model, reason), count in sorted(self._duration_count.items()):
                lines.append(
                    f'hermes_router_request_duration_seconds_count{{model="{_esc(model)}",reason="{_esc(reason)}"}} {count}'
                )

        return "\n".join(lines) + "\n"


def _esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
