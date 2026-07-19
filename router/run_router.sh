#!/usr/bin/env bash
# Start Hermes model router (idempotent).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="${HERMES_ROUTER_PID_FILE:-$HOME/.hermes/router.pid}"
PORT="${HERMES_ROUTER_PORT:-3999}"
HOST="${HERMES_ROUTER_HOST:-0.0.0.0}"
LOG="${HERMES_ROUTER_LOG:-$HOME/.hermes/logs/router.log}"

mkdir -p "$(dirname "$LOG")" "$(dirname "$PID_FILE")"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "${old_pid:-}" ]] && kill -0 "$old_pid" 2>/dev/null; then
    if curl -sf --max-time 2 "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
      echo "router: already running (pid $old_pid) http://${HOST}:${PORT}"
      exit 0
    fi
  fi
fi

if curl -sf --max-time 2 "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
  echo "router: already responding on http://${HOST}:${PORT}"
  exit 0
fi

# Load LiteLLM key from Hermes env if present
if [[ -f "$HOME/.hermes/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$HOME/.hermes/.env"
  set +a
fi

export HERMES_ROUTER_HOST="$HOST"
export HERMES_ROUTER_PORT="$PORT"
export LITELLM_UPSTREAM="${LITELLM_UPSTREAM:-http://127.0.0.1:4000}"

if [[ "${HERMES_ROUTER_FOREGROUND:-}" == "1" ]]; then
  echo "router: foreground on http://${HOST}:${PORT} → ${LITELLM_UPSTREAM}"
  exec python3 "$ROOT/server.py"
fi

nohup python3 "$ROOT/server.py" >>"$LOG" 2>&1 &
echo $! >"$PID_FILE"
sleep 0.5

if curl -sf --max-time 5 "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
  echo "router: started pid $(cat "$PID_FILE") → http://${HOST}:${PORT}"
else
  echo "router: failed to become healthy; see $LOG" >&2
  exit 1
fi
