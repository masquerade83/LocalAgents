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
| Working directory | `/Users/shailja/Documents/Kush` | Terminal/file tool CWD; list & share root |
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

## Troubleshooting

### "Model provider failed after retries" (Telegram)

Usually LiteLLM is down. Check:

```bash
curl -s http://127.0.0.1:4000/health/liveliness   # expect "I'm alive!"
tail -30 ~/.hermes/logs/errors.log                # look for APIConnectionError to :4000
launchctl list | grep litellm                     # ai.hermes.litellm should be running
```

**launchd service:** `~/Library/LaunchAgents/ai.hermes.litellm.plist` runs `~/.local/bin/litellm` directly with `WorkingDirectory` set to `~/.hermes` (not `Documents/` — macOS blocks that path for background agents).

Restart:

```bash
launchctl kickstart -k gui/$(id -u)/ai.hermes.litellm
hermes gateway restart
```

### Empty responses from qwen3-vl (image / OCR)

**Root cause:** LiteLLM's `ollama/qwen3-vl` provider uses Ollama's `/api/generate` path, which **drops or mishandles vision `image_url` blocks** → empty `content`. Text chat via LiteLLM works; only vision was broken.

**Fix in `LiteLLM/litellm_config.yaml`:**

```yaml
model: ollama_chat/qwen3-vl   # NOT ollama/qwen3-vl
```

`ollama_chat` uses `/api/chat` and preserves images correctly.

**Hermes notes (`~/.hermes/config.yaml`):**

- Default: `qwen3-vl` via `custom:litellm`
- **Do not** set `agent.reasoning_effort: none` for qwen3-vl — maps to `think:false` and can return empty content
- `qwen3-vl` needs sufficient `max_tokens` (~500+ for short text; ~4000 for OCR)

After config changes:

```bash
launchctl kickstart -k gui/$(id -u)/ai.hermes.litellm
hermes gateway restart
```

Then in Telegram: `/reset` and resend the image.

Expected gateway log: `Image routing: native (model supports vision).`

**Verified smoke test (via `:4000`):**

| Test | Result |
|------|--------|
| qwen3-vl text (`max_tokens=500`) | `Hello` ✓ |
| qwen3-vl vision OCR (`max_tokens=4000`) | ~1033 chars Sanskrit/English ✓ |

## Local file access (Kush folder)

Hermes can list and share files from `/Users/shailja/Documents/Kush` over Telegram.

### Configuration

`~/.hermes/config.yaml`:

```yaml
terminal:
  cwd: /Users/shailja/Documents/Kush

gateway:
  strict: false
  media_delivery_allow_dirs:
    - /Users/shailja/Documents/Kush

skills:
  pinned:
    - kush-file-share
```

Project instructions: `/Users/shailja/Documents/Kush/.hermes.md`  
Skill: `~/.hermes/skills/productivity/kush-file-share/SKILL.md`

### How it works

1. **List** — agent uses `search_files(target='files')` under the Kush root.
2. **Share** — agent includes a **bare absolute path** (or `MEDIA:` tag) in the reply; the gateway's `extract_local_files` attaches it to Telegram.

### Example Telegram prompts

| Prompt | Expected behavior |
|--------|-------------------|
| `List files in P_Project` | Numbered list of files (text only) |
| `Send me P_Project/report.pdf` | File attached as document |
| `Share the latest image in Photos` | Most recent image sent |

### Delivery rules

- Paths must be **outside** code fences/backticks to trigger auto-delivery.
- Files over 45 MB may fail (Telegram bot limit).
- Credential files (`.env`, keys, tokens) are denylisted in `.hermes.md` and the skill.

After config changes: `hermes gateway restart`, then `/reset` in Telegram.

## n8n workflows (Hermes stack)

Docker container `n8n` on port `5678`. Workflows are deployed via Python scripts in `~/.hermes/bin/` using the n8n API (`N8N_API_KEY` in `~/.config/n8n-mcp/env`).

| Workflow | Webhook | Deploy script |
|----------|---------|---------------|
| **Stack Health Check (Hermes)** | `GET http://127.0.0.1:5678/webhook/stack-health` | `~/.hermes/bin/create-n8n-health-workflow.py` |
| **Hermes LLM Task Template (LiteLLM)** | `POST http://127.0.0.1:5678/webhook/hermes-llm-task` | `~/.hermes/bin/create-n8n-llm-template-workflow.py` |

### Stack health check

Probes (from inside the n8n container via `host.docker.internal`):

- LiteLLM liveliness: `GET :4000/health/liveliness`
- LiteLLM models: `GET :4000/v1/models` with `Authorization: Bearer admin`
- Ollama backend: `GET :11434/api/tags`
- n8n self: `GET :5678/healthz`

```bash
python3 ~/.hermes/bin/create-n8n-health-workflow.py
curl -s http://127.0.0.1:5678/webhook/stack-health | python3 -m json.tool
```

### LLM task template (LiteLLM routing)

Routes OCR and summary tasks through LiteLLM (`http://host.docker.internal:4000/v1/chat/completions`, Bearer `admin`) — **not** direct Ollama.

| `task` | LiteLLM model | Notes |
|--------|---------------|-------|
| `ocr` | `deepseek-ocr` | Optional `image_url` for vision OCR |
| `summary` | `llama3` (default) or `hermes3` | Set `"model": "hermes3"` to override |

```bash
python3 ~/.hermes/bin/create-n8n-llm-template-workflow.py

# Summary via llama3
curl -s -X POST http://127.0.0.1:5678/webhook/hermes-llm-task \
  -H 'Content-Type: application/json' \
  -d '{"task":"summary","text":"Summarize in one sentence: LiteLLM proxies Ollama for Hermes."}'

# OCR smoke (text-only; add image_url for real OCR)
curl -s -X POST http://127.0.0.1:5678/webhook/hermes-llm-task \
  -H 'Content-Type: application/json' \
  -d '{"task":"ocr","text":"Extract all visible text."}'
```

## Integrations

| Integration | Status |
|-------------|--------|
| Telegram | Connected (polling, `@DhauladharBot`) |
| LiteLLM | Proxy at `127.0.0.1:4000` → Ollama |
| Ollama | Local at `127.0.0.1:11434` |
| n8n MCP | Enabled (`~/.hermes/mcp-installs/n8n/`) |
| n8n workflows | Health + LLM template webhooks (see above) |
| WhatsApp | Enabled but not paired |
| Home Assistant | Retrying connection |
| clawd RAG | Separate project at `clawd/rag/` |

## Security

- Keep `TELEGRAM_BOT_TOKEN` only in `~/.hermes/.env`.
- Whitelist users via `TELEGRAM_ALLOWED_USERS`.
- Rotate token via [@BotFather](https://t.me/BotFather) if exposed.
