# Hermes Switch

Local web panel to **start/stop** the end-to-end flow:

```
Telegram → Hermes Gateway → LiteLLM → Ollama
                              n8n (workflows)
```

## Quick start

```bash
chmod +x Hermes_Switch/stackctl.sh Hermes_Switch/open-panel.sh Hermes_Switch/run_switch.sh
./Hermes_Switch/open-panel.sh
```

Opens **http://127.0.0.1:9120** with toggle switches.

## Auto-start (launchd)

Install once so the panel survives reboots and restarts automatically:

```bash
cp Hermes_Switch/ai.hermes.switch.plist ~/Library/LaunchAgents/
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/ai.hermes.switch.plist
launchctl kickstart -k "gui/$(id -u)/ai.hermes.switch"
curl -s http://127.0.0.1:9120/api/status | python3 -m json.tool
```

Logs: `~/.hermes/logs/switch-launchd.log`

Restart / stop panel only:

```bash
launchctl kickstart -k gui/$(id -u)/ai.hermes.switch
launchctl bootout gui/$(id -u)/ai.hermes.switch
```

## CLI (no UI)

```bash
./Hermes_Switch/stackctl.sh status
./Hermes_Switch/stackctl.sh start all
./Hermes_Switch/stackctl.sh stop all
./Hermes_Switch/stackctl.sh stop gateway
```

## Services

| Switch | What it controls |
|--------|------------------|
| Ollama | Local LLM on `:11434` |
| LiteLLM Postgres | Docker `litellm-postgres-1` |
| LiteLLM | launchd `ai.hermes.litellm` → `:4000` |
| Hermes Gateway | launchd `ai.hermes.gateway` → Telegram |
| n8n | Docker `n8n` → `:5678` |

**Master switch:** starts/stops the full stack (stop leaves Postgres + Ollama running for faster restarts).

## Manual server

```bash
python3 Hermes_Switch/server.py
# HERMES_SWITCH_PORT=9120 (default)
```

Binds **127.0.0.1 only** — not exposed to the network.
