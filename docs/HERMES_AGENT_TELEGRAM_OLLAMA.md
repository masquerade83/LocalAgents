# Hermes Agent — Telegram + Local Ollama (Qwen3-VL 8.8B)

**Notion page:** [Hermes Agent — Telegram + Local Ollama (Qwen3-VL 8.8B)](https://app.notion.com/p/39e9eda1d5b38136a9f7cbed70bc38ac)

## Overview

Local-first **Hermes Agent** on macOS, integrated with **Telegram** and backed by **local Ollama**. Users chat via Telegram; the Hermes Gateway routes messages to the agent runtime; inference runs at `http://127.0.0.1:11434`. Vision and OCR use **Qwen3-VL 8.8B** (`qwen3-vl:latest`) as the default model. **DeepSeek-OCR 3.3B** (`deepseek-ocr:latest`) is available as a dedicated OCR model.

**Status (2026-07-15):** deployed — Telegram connected, inference via LiteLLM → Ollama.

## Architecture

```
User (Telegram) → Telegram Bot API → Hermes Gateway (~/.hermes)
  → Hermes Agent (tools, memory, skills)
  → LiteLLM proxy (127.0.0.1:4000/v1)
  → Ollama API (127.0.0.1:11434)
  → Qwen3-VL 8.8B (default) / DeepSeek-OCR 3.3B (OCR)
```

### Request flow

1. User sends text, voice, image, or file in Telegram DM.
2. Gateway receives update via **long polling**.
3. Session key: `agent:main:telegram:dm:<chat_id>`.
4. Agent calls LiteLLM at `http://127.0.0.1:4000/v1` (provider: `custom:litellm`).
5. LiteLLM forwards to Ollama at `http://127.0.0.1:11434`.
6. Images: `Image routing: native (model supports vision)` — processed by Qwen3-VL 8.8B.
7. Response sent back to Telegram.

## Access details

| Component | Access | Notes |
|-----------|--------|-------|
| Telegram bot | `@DhauladharBot` | Channel: `Mac_Hermes_Local` |
| Telegram mode | Long polling | Not webhook-based |
| Authorized user | Kush Sood (`6984780284`) | `TELEGRAM_ALLOW_ALL_USERS=false` |
| Bot token | `~/.hermes/.env` → `TELEGRAM_BOT_TOKEN` | Never store in git or Notion |
| Hermes config | `~/.hermes/config.yaml` | Model, toolsets, Telegram policy |
| Hermes secrets | `~/.hermes/.env` | Tokens and env overrides |
| Agent install | `~/.hermes/hermes-agent/` | NousResearch Hermes Agent |
| Working directory | `/Users/shailja/Documents/Kush/P_Project/Hermes_Working_Directory/` | Terminal/file tool CWD |
| LiteLLM proxy | `http://127.0.0.1:4000` | OpenAI-compat: `/v1`; master key in env |
| Ollama API | `http://127.0.0.1:11434` | Backend for LiteLLM |
| Default LLM | **Qwen3-VL 8.8B** (`qwen3-vl:latest`) | Vision + OCR; 6.1 GB |
| OCR model | **DeepSeek-OCR 3.3B** (`deepseek-ocr:latest`) | Dedicated OCR; 6.7 GB |
| Hermes Dashboard | `http://127.0.0.1:9119` | `hermes dashboard` |
| Gateway logs | `~/.hermes/logs/gateway.log` | Connection + message trace |
| n8n (optional) | `http://localhost:5678` | MCP server in config |
| clawd RAG (related) | `clawd/rag/` | Same Ollama host |

## Ollama models (local)

| Full name | Ollama tag | Size | Role |
|-----------|------------|------|------|
| **Qwen3-VL 8.8B** | `qwen3-vl:latest` | 6.1 GB | **Default** — vision, OCR |
| **DeepSeek-OCR 3.3B** | `deepseek-ocr:latest` | 6.7 GB | Dedicated OCR |
| **Hermes 3 8B** | `hermes3:8b` | 4.7 GB | General Hermes chat |
| **Meta Llama 3** | `llama3:latest` | 4.7 GB | Chat fallback |
| **Nomic Embed Text** | `nomic-embed-text:latest` | 274 MB | Embeddings |

Verify:

```bash
ollama list
curl -s http://127.0.0.1:11434/api/tags
```

## Key configuration

`~/litellm_config.yaml`:

```yaml
model_list:
  - model_name: qwen3-vl
    litellm_params:
      model: ollama/qwen3-vl
      api_base: http://127.0.0.1:11434
  - model_name: deepseek-ocr
    litellm_params:
      model: ollama/deepseek-ocr
      api_base: http://127.0.0.1:11434
  - model_name: hermes3
    litellm_params:
      model: ollama/hermes3:8b
      api_base: http://127.0.0.1:11434
  - model_name: llama3
    litellm_params:
      model: ollama/llama3
      api_base: http://127.0.0.1:11434
general_settings:
  master_key: admin
```

`~/.hermes/config.yaml` (model section):

```yaml
model:
  provider: custom:litellm
  base_url: http://127.0.0.1:4000/v1
  default: qwen3-vl
  context_length: 131072
  supports_vision: true

custom_providers:
  - name: litellm
    base_url: http://127.0.0.1:4000/v1
    key_env: LITELLM_MASTER_KEY
```

Backup (pre-LiteLLM direct Ollama): `~/.hermes/config.workingwithoutLiteLLM.yaml`

## LiteLLM scripts and auto-start

| Script | Path |
|--------|------|
| Start (idempotent) | `Hermes_Working_Directory/run_litellm.sh` |
| Stop | `Hermes_Working_Directory/stop_litellm.sh` |
| Gateway hook | `~/.hermes/hooks/litellm-startup/` (`gateway:startup`) |
| launchd service | `~/Library/LaunchAgents/ai.hermes.litellm.plist` |

## Operations

```bash
# LiteLLM
~/Documents/Kush/P_Project/Hermes_Working_Directory/run_litellm.sh
curl -s http://127.0.0.1:4000/health/liveliness
curl -s http://127.0.0.1:4000/v1/models -H "Authorization: Bearer admin"

# Gateway
hermes gateway run
hermes gateway status

# Dashboard
hermes dashboard   # → http://127.0.0.1:9119

# Ollama
ollama serve

# Health
curl -s http://127.0.0.1:11434/api/tags
tail -50 ~/.hermes/logs/gateway.log
```

### Rollback to direct Ollama

```bash
cp ~/.hermes/config.workingwithoutLiteLLM.yaml ~/.hermes/config.yaml
hermes gateway restart
```

Expected gateway log lines:

- `Connected to Telegram (polling mode)`
- `Gateway running with 1 platform(s)`
- `Image routing: native (model supports vision)`

## Integrations

| Integration | Status |
|-------------|--------|
| Telegram | Connected (polling, `@DhauladharBot`) |
| LiteLLM | Proxy at `127.0.0.1:4000` → Ollama |
| Ollama | Local at `127.0.0.1:11434` |
| n8n MCP | Enabled (`~/.hermes/mcp-installs/n8n/`) |
| WhatsApp | Enabled but not paired |
| Home Assistant | Retrying connection |
| clawd RAG | Separate project at `clawd/rag/` |

## Security

- Keep `TELEGRAM_BOT_TOKEN` only in `~/.hermes/.env`.
- Whitelist users via `TELEGRAM_ALLOWED_USERS`.
- Rotate token via [@BotFather](https://t.me/BotFather) if exposed.
