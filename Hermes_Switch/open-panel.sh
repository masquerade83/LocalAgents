#!/usr/bin/env bash
# Open the Hermes Switch panel in the default browser.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${HERMES_SWITCH_PORT:-9120}"
UID_LABEL="gui/$(id -u)"
URL="http://127.0.0.1:${PORT}/"

health_ok() {
  curl -sf --max-time 2 "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>&1
}

# Prefer launchd-managed panel when installed.
if launchctl print "${UID_LABEL}/ai.hermes.switch" >/dev/null 2>&1; then
  launchctl kickstart -k "${UID_LABEL}/ai.hermes.switch" 2>/dev/null || true
else
  chmod +x "$DIR/run_switch.sh"
  "$DIR/run_switch.sh"
fi

for _ in $(seq 1 20); do
  if health_ok; then
    open "$URL"
    exit 0
  fi
  sleep 0.25
done

echo "Hermes Switch failed to start — check ~/.hermes/logs/switch-launchd.log or hermes-switch.log" >&2
exit 1
