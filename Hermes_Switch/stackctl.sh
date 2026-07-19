#!/usr/bin/env bash
# Control Hermes + LiteLLM + Ollama + n8n stack (status / start / stop).
set -euo pipefail

UID_LABEL="gui/$(id -u)"
CLAWD="$(cd "$(dirname "$0")/.." && pwd)"
LITELLM_DIR="$CLAWD/LiteLLM"
ROUTER_DIR="$CLAWD/router"
HERMES_BIN="${HERMES_BIN:-$(command -v hermes || echo "$HOME/.local/bin/hermes")}"

svc_status() {
  local name="$1" running="false" detail=""
  case "$name" in
    ollama)
      if curl -sf --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        running="true"
        detail=":11434"
      else
        detail="not responding"
      fi
      ;;
    postgres)
      if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'litellm-postgres-1'; then
        running="true"
        detail="litellm-postgres-1"
      else
        detail="container stopped"
      fi
      ;;
    litellm)
      if curl -sf --max-time 2 http://127.0.0.1:4000/health/liveliness >/dev/null 2>&1; then
        running="true"
        detail=":4000"
      elif launchctl print "$UID_LABEL/ai.hermes.litellm" >/dev/null 2>&1; then
        detail="launchd loaded, not healthy yet"
      else
        detail="stopped"
      fi
      ;;
    router)
      if curl -sf --max-time 2 http://127.0.0.1:3999/health >/dev/null 2>&1; then
        running="true"
        detail=":3999"
      else
        detail="stopped"
      fi
      ;;
    gateway)
      gs_out="$("$HERMES_BIN" gateway status 2>&1)" || true
      if launchctl print "$UID_LABEL/ai.hermes.gateway" 2>/dev/null | grep -q 'state = running'; then
        running="true"
        detail="Telegram gateway"
      elif echo "$gs_out" | grep -qiE 'not loaded|is not loaded'; then
        detail="stopped"
      else
        running="true"
        detail="Telegram gateway"
      fi
      ;;
    n8n)
      if curl -sf --max-time 2 http://127.0.0.1:5678/healthz >/dev/null 2>&1; then
        running="true"
        detail=":5678"
      elif docker ps -a --format '{{.Names}} {{.Status}}' 2>/dev/null | grep -q '^n8n '; then
        detail="container exists, stopped"
      else
        detail="not found"
      fi
      ;;
    *)
      echo "unknown service: $name" >&2
      return 1
      ;;
  esac
  printf '{"name":"%s","running":%s,"detail":"%s"}\n' "$name" "$running" "$detail"
}

cmd_status() {
  local first=1
  printf '['
  for s in ollama postgres litellm router gateway n8n; do
    [[ $first -eq 1 ]] || printf ','
    first=0
    svc_status "$s"
  done
  printf ']\n'
}

start_ollama() {
  if curl -sf --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "ollama: already running"
    return 0
  fi
  if [[ -d /Applications/Ollama.app ]]; then
    open -a Ollama
  else
    nohup ollama serve >>"$HOME/.hermes/logs/ollama.log" 2>&1 &
  fi
  for _ in $(seq 1 30); do
    curl -sf --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && return 0
    sleep 1
  done
  echo "ollama: did not become ready" >&2
  return 1
}

stop_ollama() {
  if [[ -d /Applications/Ollama.app ]]; then
    osascript -e 'quit app "Ollama"' 2>/dev/null || true
  fi
  pkill -x ollama 2>/dev/null || true
  echo "ollama: stop requested"
}

start_postgres() {
  docker compose -f "$LITELLM_DIR/docker-compose.yml" up -d postgres
  echo "postgres: started"
}

stop_postgres() {
  docker compose -f "$LITELLM_DIR/docker-compose.yml" stop postgres
  echo "postgres: stopped"
}

start_litellm() {
  launchctl kickstart -k "$UID_LABEL/ai.hermes.litellm" 2>/dev/null \
    || launchctl bootstrap "$UID_LABEL" "$HOME/Library/LaunchAgents/ai.hermes.litellm.plist"
  echo "litellm: start requested"
}

stop_litellm() {
  launchctl bootout "$UID_LABEL/ai.hermes.litellm" 2>/dev/null || true
  if [[ -f "$HOME/.hermes/litellm.pid" ]]; then
    pid="$(cat "$HOME/.hermes/litellm.pid" 2>/dev/null || true)"
    [[ -n "${pid:-}" ]] && kill "$pid" 2>/dev/null || true
    rm -f "$HOME/.hermes/litellm.pid"
  fi
  echo "litellm: stopped"
}

start_router() {
  bash "$ROUTER_DIR/run_router.sh"
}

stop_router() {
  launchctl bootout "$UID_LABEL/ai.hermes.router" 2>/dev/null || true
  if [[ -f "$HOME/.hermes/router.pid" ]]; then
    pid="$(cat "$HOME/.hermes/router.pid" 2>/dev/null || true)"
    [[ -n "${pid:-}" ]] && kill "$pid" 2>/dev/null || true
    rm -f "$HOME/.hermes/router.pid"
  fi
  pkill -f "$ROUTER_DIR/server.py" 2>/dev/null || true
  echo "router: stopped"
}

start_gateway() {
  "$HERMES_BIN" gateway start 2>/dev/null || launchctl kickstart -k "$UID_LABEL/ai.hermes.gateway"
  echo "gateway: start requested"
}

stop_gateway() {
  "$HERMES_BIN" gateway stop 2>/dev/null || launchctl bootout "$UID_LABEL/ai.hermes.gateway" 2>/dev/null || true
  echo "gateway: stopped"
}

start_n8n() {
  docker start n8n 2>/dev/null || { echo "n8n: container not found" >&2; return 1; }
  echo "n8n: started"
}

stop_n8n() {
  docker stop n8n 2>/dev/null || true
  echo "n8n: stopped"
}

start_one() {
  case "$1" in
    ollama) start_ollama ;;
    postgres) start_postgres ;;
    litellm) start_litellm ;;
    router) start_router ;;
    gateway) start_gateway ;;
    n8n) start_n8n ;;
    *) echo "unknown: $1" >&2; return 1 ;;
  esac
}

stop_one() {
  case "$1" in
    ollama) stop_ollama ;;
    postgres) stop_postgres ;;
    litellm) stop_litellm ;;
    router) stop_router ;;
    gateway) stop_gateway ;;
    n8n) stop_n8n ;;
    *) echo "unknown: $1" >&2; return 1 ;;
  esac
}

start_all() {
  start_ollama || true
  start_postgres
  sleep 2
  start_litellm
  sleep 3
  start_router
  sleep 1
  start_n8n || true
  sleep 2
  start_gateway
}

stop_all() {
  stop_gateway
  stop_n8n || true
  stop_router
  stop_litellm
  # keep postgres + ollama running by default on stop-all (faster restarts)
  echo "stack: core stopped (postgres + ollama left running)"
}

usage() {
  cat <<EOF
Usage: stackctl.sh <status|start|stop> [service|all]

Services: ollama postgres litellm router gateway n8n

Examples:
  stackctl.sh status
  stackctl.sh start all
  stackctl.sh stop gateway
EOF
}

ACTION="${1:-status}"
TARGET="${2:-}"

case "$ACTION" in
  status)
    cmd_status
    ;;
  start)
    case "$TARGET" in
      all|"") start_all ;;
      *) start_one "$TARGET" ;;
    esac
    ;;
  stop)
    case "$TARGET" in
      all|"") stop_all ;;
      *) stop_one "$TARGET" ;;
    esac
    ;;
  *)
    usage
    exit 1
    ;;
esac
