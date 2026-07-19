# Hermes Model Routing (Option 1 + 3)

**Deployed:** 2026-07-19

## Architecture

```
Telegram → Hermes Gateway → Agent
                              ├─ Main chat (hermes3) ──────┐
                              ├─ Auxiliary vision (deepseek-ocr) ──┤
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
| Hermes `supports_vision` | `true` | `false` |
| Hermes `base_url` | `http://127.0.0.1:4000/v1` | `http://127.0.0.1:3999/v1` |
| Image routing | Same model as text (`qwen3-vl`) | Router → `deepseek-ocr` or `qwen3-vl` by content |
| Vision auxiliary | auto / main model | `deepseek-ocr` via router |
| Text chat latency | Slow (VL model always loaded) | Faster (`hermes3` / `llama3`) |
| Central routing | None — caller picks model | Router inspects `messages[]` |
| n8n LLM path | Direct LiteLLM :4000 | Can use router :3999 |

## Router rules (`clawd/router/rules.py`)

| Signal | Model |
|--------|--------|
| Session `auto` + text ≤10 words | `llama3` (tools stripped) |
| Session `auto` + general text | `hermes3` (tools stripped) |
| Session `auto` + tools + action keywords / long prompt | `qwen3-vl` (tools kept) |
| `image_url` in messages | `deepseek-ocr` |
| Image + describe/diagram keywords | `qwen3-vl` |
| Explicit `deepseek-ocr` / `qwen3-vl` | pass-through |

Router code: `clawd/router/rules.py` (selection), `clawd/router/server.py` (proxy + tool stripping).

## Config files

| File | Change |
|------|--------|
| `~/.hermes/config.yaml` | default `hermes3`, router URL, `auxiliary.vision` |
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
