#!/usr/bin/env bash
# Open the Hermes Switch panel in the default browser.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${HERMES_SWITCH_PORT:-9120}"
PIDFILE="$HOME/.hermes/hermes-switch.pid"
LOG="$HOME/.hermes/logs/hermes-switch.log"

mkdir -p "$(dirname "$LOG")"

if [[ -f "$PIDFILE" ]]; then
  old="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [[ -n "${old:-}" ]] && kill -0 "$old" 2>/dev/null; then
    open "http://127.0.0.1:${PORT}/"
    exit 0
  fi
fi

nohup python3 "$DIR/server.py" >>"$LOG" 2>&1 &
echo $! >"$PIDFILE"

for _ in $(seq 1 20); do
  if curl -sf --max-time 1 "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>&1; then
    open "http://127.0.0.1:${PORT}/"
    exit 0
  fi
  sleep 0.25
done

echo "Hermes Switch failed to start — check $LOG" >&2
exit 1
