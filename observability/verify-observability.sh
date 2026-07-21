#!/usr/bin/env bash
# Verify Hermes Prometheus + Grafana are wired to clawd/observability (not object_detection).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RED=$'\033[0;31m'; GRN=$'\033[0;32m'; NC=$'\033[0m'

ok() { echo "${GRN}✓${NC} $*"; }
fail() { echo "${RED}✗${NC} $*"; exit 1; }

echo "=== Hermes observability verify ==="
echo "Project: $ROOT/observability"
echo ""

# Prometheus config mount
mount=$(docker inspect hermes-prometheus --format '{{range .Mounts}}{{if eq .Destination "/etc/prometheus/prometheus.yml"}}{{.Source}}{{end}}{{end}}' 2>/dev/null || true)
if [[ "$mount" == "$ROOT/observability/prometheus.yml" ]]; then
  ok "Prometheus config → clawd/observability/prometheus.yml"
else
  fail "Prometheus config mount wrong: ${mount:-not running}"
fi

# Targets
python3 - "$ROOT" <<'PY'
import json, sys, urllib.request
root = sys.argv[1]
try:
    data = json.load(urllib.request.urlopen("http://127.0.0.1:9090/api/v1/targets"))
except OSError:
    print("FAIL Prometheus not reachable on :9090", file=sys.stderr)
    sys.exit(1)
targets = data["data"]["activeTargets"]
jobs = {t["labels"].get("job"): t["health"] for t in targets}
expected = ["hermes-router", "litellm", "ollama-vram", "ollama-inference", "prometheus"]
for j in expected:
    if jobs.get(j) != "up":
        print(f"FAIL target {j}: {jobs.get(j, 'missing')}", file=sys.stderr)
        sys.exit(1)
print(f"OK all Hermes targets up: {', '.join(expected)}")
PY

# Sample metrics
python3 <<'PY'
import json, urllib.request
data = json.load(urllib.request.urlopen('http://127.0.0.1:9090/api/v1/query?query=up'))
for s in data["data"]["result"]:
    m = s["metric"]
    print(f"  up job={m.get('job')} project={m.get('project','?')} = {s['value'][1]}")
PY

# Grafana datasource UID
uid=$(curl -sf -u admin:admin http://127.0.0.1:3000/api/datasources 2>/dev/null | python3 -c "import sys,json; ds=json.load(sys.stdin); print(next((d['uid'] for d in ds if d.get('uid')=='prometheus'), 'NONE'))" 2>/dev/null || echo NONE)
if [[ "$uid" == "prometheus" ]]; then
  ok "Grafana datasource uid=prometheus"
else
  echo "${RED}!${NC} Grafana missing uid=prometheus (found $uid). Run: $ROOT/observability/fix-grafana-datasource.sh"
fi

# Dashboard
curl -sf -u admin:admin http://127.0.0.1:3000/api/search?query=Hermes 2>/dev/null | python3 -c "
import sys,json
ds=json.load(sys.stdin)
if ds: print('  Dashboards:', ', '.join(d['title'] for d in ds))
else: print('  No Hermes dashboards found — restart Grafana after provisioning fix')
" 2>/dev/null || true

echo ""
echo "Prometheus UI: http://127.0.0.1:9090/targets"
echo "Grafana UI:    http://127.0.0.1:3000/d/hermes-stack-overview/hermes-stack-overview"
echo "Latency dash: http://127.0.0.1:3000/d/hermes-llm-latency/hermes-llm-latency"
echo "Try query:     up{project=\"hermes\"}"
