#!/usr/bin/env bash
# Run stack-observe and exit non-zero when alert thresholds are breached.
# Use from cron, launchd, or n8n Execute Command node.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT="$("$ROOT/scripts/stack-observe.sh" 2>/dev/null)" || true

if [[ -z "$REPORT" ]]; then
  echo '{"ok":false,"alerts":["observe:empty_report"],"issues":[],"timestamp":null}'
  exit 1
fi

export STACK_OBSERVE_REPORT="$REPORT"
python3 <<'PY'
import json, os, sys

report = json.loads(os.environ["STACK_OBSERVE_REPORT"])
alerts = []

for h in report.get("health", []):
    if not h.get("healthy") and h.get("component") not in ("litellm_models",):
        alerts.append(f"unhealthy:{h['component']}")

VRAM_WARN_MODELS = int(os.environ.get("HERMES_VRAM_WARN_MODELS", "2"))
vram = report.get("vram", {})
loaded = vram.get("models_loaded", 0)
if loaded > VRAM_WARN_MODELS:
    alerts.append(f"vram:models_loaded:{loaded}")
for m in vram.get("models", []):
    ctx = m.get("context_length") or 0
    if ctx > 8192:
        alerts.append(f"vram:high_context:{m.get('name')}:{ctx}")

orphans = report.get("integrations", {}).get("mcp_n8n", {}).get("orphan_server_processes", 0)
if orphans > 2:
    alerts.append(f"mcp:orphans:{orphans}")

calls = report.get("explainability", {}).get("recent_agent_api_calls", [])
if calls:
    last = calls[-1]
    if last.get("latency_s", 0) > 120:
        alerts.append(f"agent:slow_call:{last.get('latency_s')}s")

out = {
    "ok": len(alerts) == 0,
    "alerts": alerts,
    "issues": report.get("issues", []),
    "timestamp": report.get("timestamp"),
    "runbook": "docs/OBSERVABILITY_EXPLAINABILITY.md#alert-thresholds",
}
print(json.dumps(out, indent=2))
sys.exit(0 if out["ok"] else 1)
PY
