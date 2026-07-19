#!/usr/bin/env bash
# Start Hermes Switch web panel (idempotent).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="${HERMES_SWITCH_PID_FILE:-$HOME/.hermes/hermes-switch.pid}"
PORT="${HERMES_SWITCH_PORT:-9120}"
HOST="127.0.0.1"
LOG="${HERMES_SWITCH_LOG:-$HOME/.hermes/logs/hermes-switch.log}"
HEALTH_URL="http://${HOST}:${PORT}/api/status"

mkdir -p "$(dirname "$LOG")" "$(dirname "$PID_FILE")"

health_ok() {
  curl -sf --max-time 2 "$HEALTH_URL" >/dev/null 2>&1
}

if health_ok; then
  echo "switch: already responding on http://${HOST}:${PORT}"
  exit 0
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "${old_pid:-}" ]] && kill -0 "$old_pid" 2>/dev/null; then
    if health_ok; then
      echo "switch: already running (pid $old_pid) http://${HOST}:${PORT}"
      exit 0
    fi
    kill "$old_pid" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
fi

export HERMES_SWITCH_PORT="$PORT"

if [[ "${HERMES_SWITCH_FOREGROUND:-}" == "1" ]]; then
  echo "switch: foreground on http://${HOST}:${PORT}"
  exec python3 "$ROOT/server.py"
fi

nohup python3 "$ROOT/server.py" >>"$LOG" 2>&1 &
echo $! >"$PID_FILE"
sleep 0.5

if health_ok; then
  echo "switch: started pid $(cat "$PID_FILE") → http://${HOST}:${PORT}"
else
  echo "switch: failed to become healthy; see $LOG" >&2
  exit 1
fi
