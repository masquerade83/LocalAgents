# Hermes Model Router

Content-aware OpenAI-compatible proxy between Hermes/n8n and LiteLLM.

## Where routing lives

| File | Purpose |
|------|---------|
| **`rules.py`** | Model selection logic (`pick_model`, keywords, tool escalation) |
| **`server.py`** | HTTP proxy on `:3999`, calls `pick_model`, strips tools for non-agentic models |
| **`run_router.sh`** | Start script (foreground for launchd or background nohup) |
| **`ai.hermes.router.plist`** | launchd auto-start template |

Hermes config (`~/.hermes/config.yaml`) points `custom_providers.litellm.base_url` at `:3999`.
LiteLLM registry (`~/litellm_config.yaml`) lists model names including `auto`.

## Flow

```
Telegram → Hermes Gateway (model: auto) → :3999 router → :4000 LiteLLM → :11434 Ollama
```

## Routing rules (`rules.py`)

| Input | Model | Tools |
|-------|--------|-------|
| Session model `auto` + short text (≤10 words) | `llama3` | stripped |
| Session model `auto` + general text | `hermes3` | stripped |
| `auto` + tools + action keywords / long prompt | `qwen3-vl` | kept |
| Image in messages | `deepseek-ocr` | stripped |
| Image + describe/diagram keywords | `qwen3-vl` | kept |
| Explicit `deepseek-ocr` / `qwen3-vl` | pass-through | kept for qwen3-vl |

Action keywords (agent escalation): `run`, `terminal`, `search`, `file`, `code`, `git`, etc.

## Run

```bash
chmod +x run_router.sh
./run_router.sh
curl -s http://127.0.0.1:3999/health
launchctl kickstart -k gui/$(id -u)/ai.hermes.router   # if using launchd
```

## Env

| Variable | Default |
|----------|---------|
| `HERMES_ROUTER_PORT` | `3999` |
| `LITELLM_UPSTREAM` | `http://127.0.0.1:4000` |
| `LITELLM_MASTER_KEY` | from `~/.hermes/.env` |
| `HERMES_ROUTER_FOREGROUND` | `1` for launchd |

Logs: `~/.hermes/logs/router-launchd.log` (launchd) or `~/.hermes/logs/router.log`
