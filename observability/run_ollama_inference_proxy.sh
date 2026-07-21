#!/usr/bin/env bash
# Start Ollama inference metrics proxy (idempotent).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="${OLLAMA_PROXY_PID_FILE:-$HOME/.hermes/ollama-inference-proxy.pid}"
PROXY_PORT="${OLLAMA_PROXY_PORT:-11435}"
METRICS_PORT="${OLLAMA_INFERENCE_METRICS_PORT:-9102}"
UPSTREAM="${OLLAMA_UPSTREAM:-http://127.0.0.1:11434}"
LOG="${OLLAMA_PROXY_LOG:-$HOME/.hermes/logs/ollama-inference-proxy.log}"

mkdir -p "$(dirname "$LOG")" "$(dirname "$PID_FILE")"

if ! curl -sf --max-time 2 "${UPSTREAM}/api/tags" >/dev/null 2>&1; then
  echo "ollama-inference-proxy: Ollama not up at ${UPSTREAM}" >&2
  exit 1
fi

if curl -sf --max-time 2 "http://127.0.0.1:${METRICS_PORT}/metrics" >/dev/null 2>&1; then
  echo "ollama-inference-proxy: already running metrics :${METRICS_PORT} proxy :${PROXY_PORT}"
  exit 0
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  [[ -n "${old_pid:-}" ]] && kill "$old_pid" 2>/dev/null || true
  rm -f "$PID_FILE"
fi

python3 -c "import prometheus_client" 2>/dev/null || pip3 install prometheus_client >/dev/null

export OLLAMA_UPSTREAM="$UPSTREAM"
export OLLAMA_PROXY_PORT="$PROXY_PORT"
export OLLAMA_INFERENCE_METRICS_PORT="$METRICS_PORT"

if [[ "${OLLAMA_PROXY_FOREGROUND:-}" == "1" ]]; then
  exec python3 "$ROOT/observability/ollama_inference_proxy.py"
fi

nohup python3 "$ROOT/observability/ollama_inference_proxy.py" >>"$LOG" 2>&1 &
echo $! >"$PID_FILE"
sleep 0.5

if curl -sf --max-time 3 "http://127.0.0.1:${METRICS_PORT}/metrics" | grep -q ollama_inference_requests; then
  echo "ollama-inference-proxy: started pid $(cat "$PID_FILE") proxy :${PROXY_PORT} metrics :${METRICS_PORT}"
else
  echo "ollama-inference-proxy: failed; see $LOG" >&2
  exit 1
fi
