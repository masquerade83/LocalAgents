#!/usr/bin/env python3
"""Hermes stack observability + explainability probe.

Collects health, VRAM, recent routing decisions, and agent latency from local logs.
Read-only — safe to run on a live Mac stack.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_DIR = Path.home() / ".hermes" / "logs"
# 36 GB M3 Max: warn when >2 models loaded (3+); Option A still prefers 1 for Telegram.
VRAM_WARN_MODELS = int(os.environ.get("HERMES_VRAM_WARN_MODELS", "2"))
ROUTER_LOG = LOG_DIR / "router-launchd.error.log"
ROUTER_LOG_ALT = LOG_DIR / "router.log"
DECISIONS_LOG = LOG_DIR / "decisions.jsonl"
AGENT_LOG = LOG_DIR / "agent.log"
GATEWAY_LOG = LOG_DIR / "gateway.log"

ROUTE_RE = re.compile(
    r"request_id=\S+ route in=(?P<in_model>\S+) out=(?P<out_model>\S+) reason=(?P<reason>.+?) "
    r"status=(?P<status>\d+) (?P<ms>\d+)ms has_image=(?P<image>\w+)"
)
ROUTE_RE_LEGACY = re.compile(
    r"route in=(?P<in_model>\S+) out=(?P<out_model>\S+) reason=(?P<reason>.+?) "
    r"status=(?P<status>\d+) (?P<ms>\d+)ms has_image=(?P<image>\w+)"
)
API_CALL_RE = re.compile(
    r"API call #\d+: model=(?P<model>\S+) provider=(?P<provider>\S+) "
    r"in=(?P<in_tok>\d+) out=(?P<out_tok>\d+) total=(?P<total>\d+) latency=(?P<latency>[\d.]+)s"
)
TURN_RE = re.compile(
    r"conversation turn: session=(?P<session>\S+) model=(?P<model>\S+) "
    r"provider=(?P<provider>\S+) platform=(?P<platform>\S+) history=(?P<history>\d+)"
)


def _curl_json(url: str, timeout: float = 3.0, headers: dict[str, str] | None = None) -> tuple[bool, Any]:
    hdrs = headers or {}
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        return False, str(e)


def _curl_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _tail_lines(path: Path, n: int = 500) -> list[str]:
    if not path.is_file():
        return []
    try:
        data = path.read_text(errors="replace").splitlines()
        return data[-n:]
    except OSError:
        return []


def _read_decisions(limit: int = 10) -> list[dict[str, Any]]:
    if not DECISIONS_LOG.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in DECISIONS_LOG.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append(
                {
                    "request_id": rec.get("request_id"),
                    "trace_id": rec.get("trace_id"),
                    "requested_model": rec.get("in_model"),
                    "routed_model": rec.get("out_model"),
                    "reason": rec.get("reason"),
                    "http_status": rec.get("status"),
                    "latency_ms": rec.get("latency_ms"),
                    "has_image": rec.get("has_image"),
                    "ts": rec.get("ts"),
                    "explain": f"Router chose {rec.get('out_model')} because: {rec.get('reason')}",
                }
            )
    except OSError:
        return []
    return rows[-limit:]


def _grep_routes(lines: list[str], limit: int = 10) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for line in reversed(lines):
        m = ROUTE_RE.search(line) or ROUTE_RE_LEGACY.search(line)
        if m:
            routes.append(
                {
                    "requested_model": m.group("in_model"),
                    "routed_model": m.group("out_model"),
                    "reason": m.group("reason"),
                    "http_status": int(m.group("status")),
                    "latency_ms": int(m.group("ms")),
                    "has_image": m.group("image") == "True",
                    "explain": f"Router chose {m.group('out_model')} because: {m.group('reason')}",
                }
            )
            if len(routes) >= limit:
                break
    return list(reversed(routes))


def _grep_agent_calls(lines: list[str], limit: int = 10) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for line in reversed(lines):
        m = API_CALL_RE.search(line)
        if m:
            calls.append(
                {
                    "model": m.group("model"),
                    "provider": m.group("provider"),
                    "input_tokens": int(m.group("in_tok")),
                    "output_tokens": int(m.group("out_tok")),
                    "total_tokens": int(m.group("total")),
                    "latency_s": float(m.group("latency")),
                    "explain": (
                        f"Agent called {m.group('model')} via {m.group('provider')}; "
                        f"{m.group('total')} tokens in {m.group('latency')}s"
                    ),
                }
            )
            if len(calls) >= limit:
                break
    return list(reversed(calls))


def _last_turn(lines: list[str]) -> dict[str, Any] | None:
    for line in reversed(lines):
        m = TURN_RE.search(line)
        if m:
            return {
                "session": m.group("session"),
                "model": m.group("model"),
                "provider": m.group("provider"),
                "platform": m.group("platform"),
                "history_messages": int(m.group("history")),
            }
    return None


def _mcp_orphan_count() -> int:
    try:
        out = subprocess.run(
            ["pgrep", "-f", "n8n/server.py"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return len([x for x in out.stdout.strip().splitlines() if x.strip()])
    except (subprocess.SubprocessError, OSError):
        return -1


def probe_health() -> list[dict[str, Any]]:
    checks = [
        ("ollama", "http://127.0.0.1:11434/api/tags", None),
        ("litellm", "http://127.0.0.1:4000/health/liveliness", None),
        ("router", "http://127.0.0.1:3999/health", None),
        ("n8n", "http://127.0.0.1:5678/healthz", None),
        ("hermes_switch", "http://127.0.0.1:9120/api/status", None),
        ("prometheus", "http://127.0.0.1:9090/-/healthy", None),
        ("grafana", "http://127.0.0.1:3000/api/health", None),
        ("ollama_exporter", "http://127.0.0.1:9101/metrics", None),
        ("ollama_inference_proxy", "http://127.0.0.1:9102/metrics", None),
        ("litellm_models", "http://127.0.0.1:4000/v1/models", {"Authorization": "Bearer admin"}),
    ]
    rows: list[dict[str, Any]] = []
    for name, url, hdrs in checks:
        ok = _curl_ok(url) if name != "litellm_models" else _curl_json(url, headers=hdrs or {})[0]
        rows.append({"component": name, "url": url, "healthy": ok})
    # Gateway — launchd only
    gw_ok = False
    try:
        uid = subprocess.check_output(["id", "-u"], text=True).strip()
        out = subprocess.check_output(
            ["launchctl", "print", f"gui/{uid}/ai.hermes.gateway"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        gw_ok = "state = running" in out
    except (subprocess.CalledProcessError, OSError):
        pass
    rows.append({"component": "gateway", "url": "launchd:ai.hermes.gateway", "healthy": gw_ok})
    # Postgres docker
    pg_ok = False
    try:
        out = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True, timeout=5)
        pg_ok = "litellm-postgres-1" in out.splitlines()
    except (subprocess.CalledProcessError, OSError):
        pass
    rows.append({"component": "postgres", "url": "docker:litellm-postgres-1", "healthy": pg_ok})
    return rows


def probe_vram() -> dict[str, Any]:
    ok, data = _curl_json("http://127.0.0.1:11434/api/ps")
    if not ok:
        return {"ok": False, "error": data, "models_loaded": 0, "models": []}
    models = data.get("models", [])
    total_vram = sum(int(m.get("size_vram", 0)) for m in models)
    loaded = len(models)
    warn = loaded > VRAM_WARN_MODELS
    if loaded <= 1:
        explain_suffix = "OK for Option A (single hot model)."
    elif loaded <= VRAM_WARN_MODELS:
        explain_suffix = f"OK on 36 GB ({loaded} models); Option A prefers 1 for Telegram."
    else:
        explain_suffix = f"WARNING: {loaded} models — hang risk even on 36 GB."
    return {
        "ok": True,
        "models_loaded": loaded,
        "warn_threshold": VRAM_WARN_MODELS,
        "total_vram_gb": round(total_vram / 1e9, 2),
        "warn_multi_model": warn,
        "models": [
            {
                "name": m.get("name"),
                "vram_gb": round(int(m.get("size_vram", 0)) / 1e9, 2),
                "context_length": m.get("context_length"),
            }
            for m in models
        ],
        "explain": f"{loaded} model(s) in VRAM ({round(total_vram/1e9,1)} GB). {explain_suffix}",
    }


def workflow_map() -> list[dict[str, str]]:
    return [
        {"step": 1, "module": "Telegram", "role": "User entry (@DhauladharBot)", "observable_via": "gateway.log"},
        {"step": 2, "module": "Hermes Gateway", "role": "Session, tools, MCP", "observable_via": "gateway.log, agent.log"},
        {"step": 3, "module": "Hermes Agent", "role": "LLM loop, tool calls", "observable_via": "agent.log, errors.log"},
        {"step": 4, "module": "Model Router :3999", "role": "Content-aware model pick + explain reason", "observable_via": "router-launchd.error.log"},
        {"step": 5, "module": "LiteLLM :4000", "role": "Registry, auth, spend logs", "observable_via": ":4000/ui, Postgres LiteLLM_SpendLogs"},
        {"step": 6, "module": "Ollama :11434", "role": "Inference / VRAM", "observable_via": "/api/ps, /api/tags"},
        {"step": 7, "module": "n8n :5678", "role": "Webhooks, MCP tools (optional)", "observable_via": "stack-health webhook, mcp health"},
        {"step": 8, "module": "Hermes Switch :9120", "role": "Start/stop + /api/observe", "observable_via": "/api/status, /api/observe"},
    ]


def build_report() -> dict[str, Any]:
    route_lines = _tail_lines(ROUTER_LOG) or _tail_lines(ROUTER_LOG_ALT)
    agent_lines = _tail_lines(AGENT_LOG)
    health = probe_health()
    vram = probe_vram()
    routes = _read_decisions(10) or _grep_routes(route_lines)
    agent_calls = _grep_agent_calls(agent_lines)
    last_turn = _last_turn(agent_lines)
    orphans = _mcp_orphan_count()

    all_ok = all(h["healthy"] for h in health if h["component"] not in ("litellm_models",))
    issues: list[str] = []
    if not all_ok:
        issues.extend(f"{h['component']} unhealthy" for h in health if not h["healthy"])
    if vram.get("warn_multi_model"):
        n = vram.get("models_loaded", 0)
        issues.append(f"{n} models loaded in Ollama VRAM (warn > {VRAM_WARN_MODELS})")
    if orphans > 2:
        issues.append(f"n8n MCP orphan processes: {orphans} (expected ≤2)")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ok": len(issues) == 0,
        "issues": issues,
        "health": health,
        "vram": vram,
        "explainability": {
            "workflow": workflow_map(),
            "last_agent_turn": last_turn,
            "recent_router_decisions": routes,
            "recent_agent_api_calls": agent_calls,
            "request_path": "Telegram → Gateway → Agent → Router :3999 → LiteLLM :4000 → Ollama :11434",
            "jupyter_path": "Notebook → jl_ollama.py → Ollama :11434 direct (qwen2.5:0.5b)",
        },
        "integrations": {
            "telegram": {"bot": "@DhauladharBot", "log": str(GATEWAY_LOG)},
            "mcp_n8n": {"orphan_server_processes": orphans, "fix": "n8n/fix-mcp.sh"},
            "litellm_ui": "http://127.0.0.1:4000/ui",
            "hermes_dashboard": "http://127.0.0.1:9119",
        },
        "log_paths": {
            "gateway": str(GATEWAY_LOG),
            "agent": str(AGENT_LOG),
            "router": str(ROUTER_LOG if ROUTER_LOG.is_file() else ROUTER_LOG_ALT),
            "decisions": str(DECISIONS_LOG),
            "errors": str(LOG_DIR / "errors.log"),
            "litellm": str(LOG_DIR / "litellm-launchd.log"),
        },
    }


def main() -> None:
    print(json.dumps(build_report(), indent=2))


if __name__ == "__main__":
    main()
