# Hermes Agent — Telegram + Local Ollama (Qwen3-VL 8.8B)

**Notion page:** [Hermes Agent — Telegram + Local Ollama (Qwen3-VL 8.8B)](https://app.notion.com/p/39e9eda1d5b38136a9f7cbed70bc38ac)

## Overview

Local-first **Hermes Agent** on macOS, integrated with **Telegram** and backed by **local Ollama**. Users chat via Telegram; the Hermes Gateway routes messages to the agent runtime; inference runs at `http://127.0.0.1:11434`. Vision and OCR use **Qwen3-VL 8.8B** (`qwen3-vl:latest`) as the default model. **DeepSeek-OCR 3.3B** (`deepseek-ocr:latest`) is available as a dedicated OCR model.

**Status (2026-07-15):** deployed and working — Telegram connected, Ollama inference confirmed.

## Architecture

```
User (Telegram) → Telegram Bot API → Hermes Gateway (~/.hermes)
  → Hermes Agent (tools, memory, skills)
  → Ollama API (127.0.0.1:11434/v1)
  → Qwen3-VL 8.8B (default) / DeepSeek-OCR 3.3B (OCR)
```

### Request flow

1. User sends text, voice, image, or file in Telegram DM.
2. Gateway receives update via **long polling**.
3. Session key: `agent:main:telegram:dm:<chat_id>`.
4. Agent calls Ollama OpenAI-compatible API at `http://127.0.0.1:11434/v1`.
5. Images: `Image routing: native (model supports vision)` — processed by Qwen3-VL 8.8B.
6. Response sent back to Telegram.

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
| Ollama API | `http://127.0.0.1:11434` | OpenAI-compat: `/v1` |
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

`~/.hermes/config.yaml` (model section):

```yaml
model:
  provider: ollama-launch
  base_url: http://127.0.0.1:11434/v1
  default: qwen3-vl

providers:
  ollama-launch:
    default_model: qwen3-vl
    models:
      - qwen3-vl:latest
      - deepseek-ocr:latest
      - hermes3:8b
      - llama3:latest
```

## Operations

```bash
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

Expected gateway log lines:

- `Connected to Telegram (polling mode)`
- `Gateway running with 1 platform(s)`
- `Image routing: native (model supports vision)`

## Integrations

| Integration | Status |
|-------------|--------|
| Telegram | Connected (polling, `@DhauladharBot`) |
| Ollama | Local at `127.0.0.1:11434` |
| n8n MCP | Enabled (`~/.hermes/mcp-installs/n8n/`) |
| WhatsApp | Enabled but not paired |
| Home Assistant | Retrying connection |
| clawd RAG | Separate project at `clawd/rag/` |

## Security

- Keep `TELEGRAM_BOT_TOKEN` only in `~/.hermes/.env`.
- Whitelist users via `TELEGRAM_ALLOWED_USERS`.
- Rotate token via [@BotFather](https://t.me/BotFather) if exposed.
