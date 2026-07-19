# Hermes Telegram — Slow / No Response (Troubleshooting)

**Date:** 2026-07-19  
**Symptom:** Telegram replies taking 5–70 minutes; sometimes no response for 10–15+ minutes; bot appears frozen.

---

## Issue (detailed)

### What users saw

- Simple messages like **“What is life”** or **“Waiting for it”** took **5–15 minutes**.
- **Image analysis** took up to **70 minutes** (`4182s` in gateway logs).
- Telegram felt **dead** during long runs — new messages not processed, `getUpdates consumer wedged` warnings.

### What was *not* broken

| Component | Status |
|-----------|--------|
| Router `:3999` | Healthy; routing adds ~0–4ms |
| LiteLLM `:4000` | Healthy (`admin` master key works) |
| Ollama `:11434` | Running |
| Hermes gateway | Running but **blocked** on long agent work |

A direct test `auto` → llama3 via router completed in **~4 seconds**. The slowness was **per-request model + payload size**, not infrastructure down.

---

## Root causes

### 1. Router used **full chat history** for model selection (critical)

`pick_model()` called `extract_text(messages)`, which concatenated **every** message — including multi‑KB vision pre-analysis injected after an image.

After one image, history looked like:

```
User: Analyze image
Assistant: [3100 chars of vision description…]
User: What is life
```

The router counted **thousands of words** in the combined text → `wants_agent_model()` returned true (`>30 words`) → **every subsequent message routed to qwen3-vl**.

**Evidence:** Router log showed `out=qwen3-vl reason=agent tools + action keywords or long prompt` for “What is life” (3 words).

### 2. **qwen3-vl** used for most Telegram text (critical)

qwen3-vl (8.8B vision model, ~11GB VRAM) is correct for **images** but **10–20× slower** than hermes3/llama3 on **18K+ token** agent prompts with tools.

| Model route | Typical latency (18K tokens in) |
|-------------|----------------------------------|
| llama3 | ~4–20s |
| hermes3 | ~30–90s |
| qwen3-vl | **90s – 26min** |

**Evidence (agent.log):**

```
API call #1: model=auto in=18735 … latency=1304.2s
API call #1: model=auto in=20158 … latency=878.9s   ← "What is life"
```

### 3. **~18–23K input tokens** on every agent turn (major)

Telegram had **17 platform toolsets** + **hermes-cli** + **8 n8n MCP tools** → huge tool schemas sent on every LLM call.

**Evidence:** `in=17929`, `in=22735` on routine chat turns.

### 4. **Double vision** on images (major)

Flow before fix:

1. Gateway **pre-analyzed** image via `vision_analyze` + qwen3-vl (`image_input_mode: auto` → text path, ~10 min).
2. Agent sometimes called **`vision_analyze` again** (~641s).
3. Then main agent call on qwen3-vl with full history.

Total wall time for one image: **70 minutes**.

### 5. **Gateway single-thread blocking** (symptom amplifier)

One long agent run blocked Telegram polling → `getUpdates consumer appears wedged` → user sends `/reset` or more messages → queue backlog.

### 6. **MoA + Copilot auth polling** (minor noise)

`moa.enabled: true` triggered Copilot token validation every ~15s during long waits (failed PAT checks in errors.log). Did not cause the main delay but added log noise and CPU.

### 7. **LiteLLM expired API keys** (intermittent)

46× `Expired Key` errors in litellm error log — affects non-`admin` keys stored in Postgres, not the main Hermes path.

---

## Resolution (applied 2026-07-19)

### A. Router (`clawd/router/rules.py`)

| Change | Effect |
|--------|--------|
| `extract_last_user_text()` — route on **latest user message only** | “What is life” after image → **llama3**, not qwen3-vl |
| `wants_agent_model()` — **action keywords only** (removed `>30 words`) | Text chat stays on hermes3/llama3 unless user asks to run/search/file/etc. |
| Images unchanged | Any `image_url` → **qwen3-vl** always |

### B. Hermes config (`~/.hermes/config.yaml`)

| Setting | Before | After |
|---------|--------|-------|
| `platform_toolsets.telegram` | 17 toolsets | **7** (file, web, vision, terminal, memory, skills, clarify) |
| `toolsets` global | hermes-cli + web | **web only** |
| `mcp_servers.n8n.tools.include` | 8 tools | **4** (health, find/list workflows, recent_failures) |
| `agent.max_turns` | 150 | **40** |
| `moa.enabled` | true | **false** |
| `model.supports_vision` | false | **true** |
| `agent.image_input_mode` | auto (text pre-analyze) | **native** (single pass → router → qwen3-vl) |

### C. Expected behavior after fix

| User input | Model | Expected time |
|------------|-------|----------------|
| “hi” / short text | llama3 | ~5–20s |
| General chat | hermes3 | ~30–90s |
| “run terminal …” / “search web …” | qwen3-vl | slower but intentional |
| Image | qwen3-vl (once) | 1–3 min typical (hardware dependent) |

---

## Apply / restart

```bash
# Reload router (launchd)
launchctl kickstart -k gui/$(id -u)/ai.hermes.router

# Reload gateway (picks up config.yaml)
hermes gateway restart

# In Telegram — clear bloated session
/reset
```

---

## Verify routing

```bash
# Should show llama3 or hermes3 for short text (not qwen3-vl)
grep "route in=auto" ~/.hermes/logs/router.log | tail -5

# Token count should drop (target <10K for simple chat)
grep "latency=" ~/.hermes/logs/agent.log | tail -5
```

---

## If still slow

1. **`/model llama3`** — force fast model for testing.
2. Check Ollama loaded model: `curl -s http://127.0.0.1:11434/api/ps` — qwen3-vl loaded during text chat means something still escalates wrong.
3. LiteLLM expired keys: LiteLLM UI → Keys → remove expired keys, or use `admin` master key only.
4. Gateway stuck: `hermes gateway restart`.

---

## Related docs

- `docs/HERMES_MODEL_ROUTING.md` — routing architecture
- `router/routing.yaml` — explicit policy file
- `router/README.md` — router rules table
