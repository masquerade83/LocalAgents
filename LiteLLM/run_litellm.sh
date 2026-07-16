#!/usr/bin/env bash
# Start LiteLLM stack: Postgres (Docker) + proxy on :4000.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="${LITELLM_CONFIG:-$DIR/litellm_config.yaml}"
PORT="${LITELLM_PORT:-4000}"
LOG="${LITELLM_LOG:-$HOME/.hermes/logs/litellm.log}"
PIDFILE="${LITELLM_PIDFILE:-$HOME/.hermes/litellm.pid}"
DATABASE_URL="${DATABASE_URL:-postgresql://litellm:litellm@127.0.0.1:5432/litellm}"

mkdir -p "$(dirname "$LOG")" "$(dirname "$PIDFILE")"

health_check() {
  curl -sf --max-time 2 "http://127.0.0.1:${PORT}/health/liveliness" >/dev/null 2>&1
}

wait_for_postgres() {
  for _ in $(seq 1 30); do
    if docker compose -f "$DIR/docker-compose.yml" exec -T postgres pg_isready -U litellm -d litellm >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "Postgres did not become ready in time" >&2
  return 1
}

echo "Starting LiteLLM Postgres..."
docker compose -f "$DIR/docker-compose.yml" up -d postgres
wait_for_postgres

if health_check; then
  echo "LiteLLM already healthy on port ${PORT}"
  exit 0
fi

if [[ -f "$PIDFILE" ]]; then
  old_pid="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [[ -n "${old_pid:-}" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "Stopping stale LiteLLM process ${old_pid}"
    kill "$old_pid" 2>/dev/null || true
    sleep 2
  fi
  rm -f "$PIDFILE"
fi

LITELLM_BIN="${LITELLM_BIN:-}"
if [[ -z "$LITELLM_BIN" ]]; then
  if command -v litellm >/dev/null 2>&1; then
    LITELLM_BIN="$(command -v litellm)"
  elif [[ -x "$HOME/.local/bin/litellm" ]]; then
    LITELLM_BIN="$HOME/.local/bin/litellm"
  else
    echo "litellm not found in PATH or $HOME/.local/bin/litellm" >&2
    exit 1
  fi
fi

export DATABASE_URL
export UI_USERNAME="${UI_USERNAME:-admin}"
export UI_PASSWORD="${UI_PASSWORD:-admin}"

# Vision via Ollama requires Pillow in the LiteLLM venv.
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$HOME/.local/share/uv/tools/litellm/bin/python" Pillow prisma >/dev/null 2>&1 || true
fi

echo "Starting LiteLLM proxy (config=${CONFIG}, port=${PORT})"
if [[ "${LITELLM_FOREGROUND:-}" == "1" ]]; then
  echo "Running LiteLLM in foreground (launchd mode)"
  exec "$LITELLM_BIN" --config "$CONFIG" --port "$PORT"
fi

nohup "$LITELLM_BIN" --config "$CONFIG" --port "$PORT" >>"$LOG" 2>&1 &
echo $! >"$PIDFILE"

for _ in $(seq 1 60); do
  if health_check; then
    echo "LiteLLM ready on http://127.0.0.1:${PORT} (pid $(cat "$PIDFILE"))"
    echo "Dashboard: http://127.0.0.1:${PORT}/ui  (admin / admin)"
    exit 0
  fi
  sleep 1
done

echo "LiteLLM did not become healthy within 60s — check ${LOG}" >&2
exit 1
