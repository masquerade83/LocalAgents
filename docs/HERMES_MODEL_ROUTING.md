# Hermes Model Routing (Option 1 + 3)

**Deployed:** 2026-07-19

## Architecture

```
Telegram → Hermes Gateway → Agent
                              ├─ Main chat (hermes3) ──────┐
                              ├─ Auxiliary vision (qwen3-vl) ──┤
                              └─ Tools (no LLM)                    │
                                                                    ▼
n8n webhooks ──────────────────────────────────────→ Model Router :3999
                                                                    │
                                                                    ▼
                                                          LiteLLM :4000
                                                                    │
                                                                    ▼
                                                          Ollama :11434
```

## Before vs After

| Aspect | Before | After |
|--------|--------|-------|
| Hermes default model | `qwen3-vl` (heavy VL for all text) | `hermes3` (fast text) |
| Hermes `supports_vision` | `true` | `true` (native images → router → qwen3-vl) |
| Hermes `base_url` | `http://127.0.0.1:4000/v1` | `http://127.0.0.1:3999/v1` |
| Image routing | Same model as text (`qwen3-vl`) | Router → **`qwen3-vl` always** for `image_url` |
| Vision auxiliary | auto / main model | **`qwen3-vl`** via router (`routing.image_model`) |
| Text chat latency | Slow (VL model always loaded) | Faster (`hermes3` / `llama3`) |
| Central routing | None — caller picks model | Router inspects `messages[]` |
| n8n LLM path | Direct LiteLLM :4000 | Can use router :3999 |

## Router rules (`clawd/router/rules.py`)

| Signal | Model |
|--------|--------|
| Session `auto` + **latest user** text ≤10 words | `llama3` (tools stripped) |
| Session `auto` + general **latest user** text | `hermes3` (tools stripped) |
| Session `auto` + **action keywords in latest user msg** | `qwen3-vl` (tools kept) |
| **Any `image_url` in messages** | **`qwen3-vl` (always)** |
| Explicit `deepseek-ocr` | pass-through (text OCR tasks only) |
| Explicit `qwen3-vl` | pass-through |

**Important:** Text routing uses the **latest user message only**, not full session history (fixes post-image qwen3-vl lock-in). See `docs/HERMES_TELEGRAM_PERFORMANCE.md`.

Router code: `clawd/router/rules.py` (selection), `clawd/router/server.py` (proxy + tool stripping).

## Config files

| File | Change |
|------|--------|
| `~/.hermes/config.yaml` | default `auto`, router URL, `routing.image_model: qwen3-vl`, `auxiliary.vision: qwen3-vl` |
| `clawd/router/routing.yaml` | explicit image/text routing policy |
| `clawd/router/rules.py` | `IMAGE_MODEL = qwen3-vl` |
| `clawd/router/server.py` | proxy on :3999 |
| `clawd/Hermes_Switch/stackctl.sh` | router start/stop in stack |

## Operations

```bash
# Start router
clawd/router/run_router.sh

# Or via Hermes Switch stack
Hermes_Switch/stackctl.sh start router

# Restart gateway after config change
hermes gateway restart

# Test text route
curl -s http://127.0.0.1:3999/v1/chat/completions \
  -H "Authorization: Bearer admin" \
  -H "Content-Type: application/json" \
  -d '{"model":"hermes3","messages":[{"role":"user","content":"Say OK"}],"max_tokens":16}'

# Health
curl -s http://127.0.0.1:3999/health
```

Logs: `~/.hermes/logs/router.log`

## Bypass router (debug)

Point clients at `http://127.0.0.1:4000/v1` directly for raw LiteLLM access.
