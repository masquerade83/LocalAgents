#!/usr/bin/env bash
# Start Ollama VRAM Prometheus exporter (idempotent).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="${OLLAMA_EXPORTER_PID_FILE:-$HOME/.hermes/ollama-exporter.pid}"
PORT="${OLLAMA_EXPORTER_PORT:-9101}"
HOST="${OLLAMA_EXPORTER_HOST:-127.0.0.1}"
LOG="${OLLAMA_EXPORTER_LOG:-$HOME/.hermes/logs/ollama-exporter.log}"

mkdir -p "$(dirname "$LOG")" "$(dirname "$PID_FILE")"

if curl -sf --max-time 2 "http://${HOST}:${PORT}/metrics" >/dev/null 2>&1; then
  echo "ollama-exporter: already running http://${HOST}:${PORT}/metrics"
  exit 0
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  [[ -n "${old_pid:-}" ]] && kill "$old_pid" 2>/dev/null || true
  rm -f "$PID_FILE"
fi

export OLLAMA_EXPORTER_HOST="$HOST"
export OLLAMA_EXPORTER_PORT="$PORT"

if [[ "${OLLAMA_EXPORTER_FOREGROUND:-}" == "1" ]]; then
  exec python3 "$ROOT/observability/ollama_vram_exporter.py"
fi

nohup python3 "$ROOT/observability/ollama_vram_exporter.py" >>"$LOG" 2>&1 &
echo $! >"$PID_FILE"
sleep 0.3

if curl -sf --max-time 2 "http://${HOST}:${PORT}/metrics" >/dev/null 2>&1; then
  echo "ollama-exporter: started pid $(cat "$PID_FILE") → http://${HOST}:${PORT}/metrics"
else
  echo "ollama-exporter: failed to start; see $LOG" >&2
  exit 1
fi
