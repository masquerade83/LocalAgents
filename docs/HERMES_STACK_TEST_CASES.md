# Hermes Stack — Test Case Document

**Version:** 2026-07-19  
**Scope:** Layer, integration, and end-to-end tests for the local Hermes stack  
**Architecture reference:** [HERMES_AGENT_TELEGRAM_OLLAMA.md](./HERMES_AGENT_TELEGRAM_OLLAMA.md)  
**Latest automated run:** [E2E_TEST_RESULTS.md](./E2E_TEST_RESULTS.md) (2026-07-19 00:43 IST)

---

## Overview

The Hermes stack is a local-first pipeline:

```
Telegram → Hermes Gateway → LiteLLM (:4000) → Ollama (:11434)
                              ↕
                         n8n (:5678) webhooks
                              ↕
                    Neo4j / GraphRAG (optional)
```

Hermes Switch (`:9120`) provides a web panel and CLI to start/stop stack services.

---

## Test environment

| Component | URL / endpoint | Auth pattern | Config / deploy path |
|-----------|----------------|--------------|----------------------|
| **Ollama** | `http://127.0.0.1:11434` | None (local) | `ollama serve` |
| **LiteLLM proxy** | `http://127.0.0.1:4000` | `Authorization: Bearer <LITELLM_MASTER_KEY>` | `LiteLLM/litellm_config.yaml`; launchd `ai.hermes.litellm` |
| **LiteLLM UI** | `http://127.0.0.1:4000/ui` | Basic auth `admin` / `admin` (default) | Same as above |
| **Postgres (LiteLLM)** | `127.0.0.1:5432` | `litellm` / `litellm` | `LiteLLM/docker-compose.yml` → container `litellm-postgres-1` |
| **Hermes Gateway** | launchd (no HTTP health port) | N/A | `~/.hermes/config.yaml`, `~/.hermes/.env` |
| **Hermes Dashboard** | `http://127.0.0.1:9119` | N/A | `hermes dashboard` |
| **Telegram bot** | `@DhauladharBot` (long polling) | `TELEGRAM_BOT_TOKEN` in `~/.hermes/.env` | Whitelist user `6984780284` |
| **n8n UI** | `http://127.0.0.1:5678` | Session login | Docker container `n8n` |
| **n8n API** | `http://127.0.0.1:5678/api/v1/*` | `X-N8N-API-KEY: <N8N_API_KEY>` | `~/.hermes/.env` |
| **n8n webhooks** | `GET /webhook/stack-health`, `POST /webhook/hermes-llm-task` | None (production webhooks) | Deploy via scripts below |
| **Hermes Switch** | `http://127.0.0.1:9120` | Localhost only | `Hermes_Switch/` (see branch note) |
| **Neo4j Browser** | `http://127.0.0.1:7474` | `neo4j` / `neo4j_local_dev` | `neo4j/docker-compose.yml` |
| **Neo4j Bolt** | `bolt://127.0.0.1:7687` | Same credentials | Same |
| **GraphRAG UI** | Streamlit (default `:8501` when running) | Localhost | `knowledge/app.py` on branch `pr/graphrag-knowledge` |

### Environment variables (never commit raw values)

| Variable | Location | Used by |
|----------|----------|---------|
| `LITELLM_MASTER_KEY` | `~/.hermes/.env` | Hermes → LiteLLM |
| `TELEGRAM_BOT_TOKEN` | `~/.hermes/.env` | Gateway |
| `N8N_API_KEY` | `~/.hermes/.env`, `~/.config/n8n-mcp/env` | n8n API + MCP |
| `N8N_BASE_URL` | `~/.config/n8n-mcp/env` | n8n MCP (`http://127.0.0.1:5678`) |
| `DATABASE_URL` | `LiteLLM/litellm_config.yaml` | LiteLLM Postgres store |

### n8n workflow deploy scripts

| Script | Purpose |
|--------|---------|
| `~/.hermes/bin/create-n8n-health-workflow.py` | Create/update **Stack Health Check (Hermes)** → webhook `stack-health` |
| `~/.hermes/bin/create-n8n-llm-template-workflow.py` | Create/update **Hermes LLM Task Template (LiteLLM)** → webhook `hermes-llm-task` |
| `~/.hermes/mcp-installs/n8n/server.py` | Hermes MCP server (11 tools) |
| `~/.config/n8n-mcp/env` | Secure MCP env (mode `600`) |

Deploy workflows (requires `N8N_API_KEY`):

```bash
python3 ~/.hermes/bin/create-n8n-health-workflow.py
python3 ~/.hermes/bin/create-n8n-llm-template-workflow.py
```

### LiteLLM / Postgres scripts

| Script | Purpose |
|--------|---------|
| `LiteLLM/run_litellm.sh` | Start Postgres + LiteLLM proxy on `:4000` |
| `LiteLLM/setup_db.sh` | One-time Prisma schema push for LiteLLM UI |
| `~/Documents/Kush/P_Project/Hermes_Working_Directory/run_litellm.sh` | Legacy working-dir copy (gateway hook) |

### Hermes Switch (repo note)

`Hermes_Switch/` lives on branch `2026-06-03-2cg9` / `pr/hermes-switch`. If missing locally:

```bash
git checkout 2026-06-03-2cg9 -- Hermes_Switch/
```

**2026-07-19 E2E:** process on `:9120` was running but workspace copy was absent — treat as **DEGRADED** until restored.

### GraphRAG cross-reference

Full GraphRAG test procedures: `knowledge/TESTING_AND_TUNING.md` (on branch `pr/graphrag-knowledge`). Covers Neo4j graph health, Chroma vectors, hybrid retrieval, and Streamlit Q&A.

---

## Quick smoke script

Run from workspace root. Uses `$LITELLM_KEY` from env or defaults to config value `admin` for local dev.

```bash
export LITELLM_KEY="${LITELLM_MASTER_KEY:-admin}"
echo "=== Hermes Stack Smoke ==="
curl -sf http://127.0.0.1:11434/api/tags >/dev/null && echo "OK Ollama" || echo "FAIL Ollama"
nc -z 127.0.0.1 5432 && echo "OK Postgres port" || echo "FAIL Postgres"
curl -sf http://127.0.0.1:4000/health/liveliness >/dev/null && echo "OK LiteLLM" || echo "FAIL LiteLLM"
launchctl list | grep -q ai.hermes.gateway && echo "OK Gateway launchd" || echo "FAIL Gateway"
docker ps --format '{{.Names}}' | grep -qx n8n && echo "OK n8n" || echo "FAIL n8n"
curl -sf http://127.0.0.1:5678/webhook/stack-health | grep -q '"ok"' && echo "OK stack-health" || echo "FAIL stack-health"
curl -sf http://127.0.0.1:9120/api/status >/dev/null && echo "OK Hermes Switch" || echo "SKIP/DEGRADED Switch"
docker ps --filter name=neo4j --format '{{.Status}}' | grep -qi healthy && echo "OK Neo4j" || echo "FAIL Neo4j"
echo "=== Done — see docs/E2E_TEST_RESULTS.md for last full run ==="
```

---

## Layer tests

### TC-001: Ollama API tags
- **Layer:** Ollama
- **Priority:** P0
- **Preconditions:** Ollama running (`ollama serve` or macOS app); port `11434` free
- **Procedure:**
  1. `curl -sS -w "\nHTTP:%{http_code}\n" --max-time 10 http://127.0.0.1:11434/api/tags`
  2. Optional: `ollama list`
- **Expected result:** HTTP 200; JSON with `models` array containing at least `qwen3-vl`, `deepseek-ocr`, `hermes3:8b`, `llama3`
- **Validation:** `http_code == 200`; `models` length ≥ 4; response time typically &lt; 50 ms
- **Failure triage:** Connection refused → start Ollama; empty models → `ollama pull qwen3-vl deepseek-ocr hermes3:8b llama3`
- **Last run (2026-07-19):** **PASS** — 8 models, ~3 ms

---

### TC-002: Ollama direct generate (llama3)
- **Layer:** Ollama
- **Priority:** P1
- **Preconditions:** TC-001 pass; `llama3:latest` pulled
- **Procedure:**
  1. ```bash
     curl -sS --max-time 90 -X POST http://127.0.0.1:11434/api/generate \
       -H 'Content-Type: application/json' \
       -d '{"model":"llama3:latest","prompt":"Say OK","stream":false}'
     ```
- **Expected result:** HTTP 200; JSON `response` contains short affirmative text (e.g. `OK`)
- **Validation:** `.response` non-empty; latency typically 0.5–5 s on Apple Silicon
- **Failure triage:** Model not found → `ollama pull llama3`; timeout → check `ollama ps` for stuck runner
- **Last run (2026-07-19):** **PASS** — ~0.62 s → `OK!`

---

### TC-003: Postgres LiteLLM DB connectivity
- **Layer:** Postgres
- **Priority:** P0
- **Preconditions:** Docker running; `cd LiteLLM && docker compose up -d postgres`
- **Procedure:**
  1. `nc -z 127.0.0.1 5432 && echo OPEN`
  2. `docker ps --filter name=litellm-postgres-1 --format '{{.Status}}'`
  3. `docker inspect litellm-postgres-1 --format '{{.State.Health.Status}}'`
  4. `docker exec litellm-postgres-1 psql -U litellm -d litellm -c 'SELECT 1;'`
- **Expected result:** Port open; container **healthy**; `SELECT 1` returns one row
- **Validation:** Health status `healthy`; psql exit code 0
- **Failure triage:** Container down → `docker compose -f LiteLLM/docker-compose.yml up -d postgres`; schema missing → run `LiteLLM/setup_db.sh`
- **Last run (2026-07-19):** **PASS**

---

### TC-004: LiteLLM liveliness
- **Layer:** LiteLLM
- **Priority:** P0
- **Preconditions:** LiteLLM on `:4000` (`LiteLLM/run_litellm.sh` or launchd `ai.hermes.litellm`)
- **Procedure:**
  1. `curl -sS -w "\nHTTP:%{http_code}\n" http://127.0.0.1:4000/health/liveliness`
- **Expected result:** HTTP 200; body contains `I'm alive!`
- **Validation:** Exact string match (case-sensitive)
- **Failure triage:** Connection refused → `launchctl kickstart -k gui/$(id -u)/ai.hermes.litellm` or `./LiteLLM/run_litellm.sh`; check `~/.hermes/logs/litellm.log`
- **Last run (2026-07-19):** **PASS** — ~3 ms

---

### TC-005: LiteLLM model registry
- **Layer:** LiteLLM
- **Priority:** P0
- **Preconditions:** TC-004 pass; `LITELLM_MASTER_KEY` set (or use local default)
- **Procedure:**
  1. ```bash
     curl -sS -H "Authorization: Bearer ${LITELLM_MASTER_KEY:-admin}" \
       http://127.0.0.1:4000/v1/models
     ```
- **Expected result:** HTTP 200; `data[]` includes `qwen3-vl`, `deepseek-ocr`, `hermes3`, `llama3`
- **Validation:** All four model IDs present; count ≥ 4
- **Failure triage:** 401 → fix key in `~/.hermes/.env`; missing models → check `LiteLLM/litellm_config.yaml` and restart LiteLLM
- **Last run (2026-07-19):** **PASS** — ~36 ms, 4 models

---

### TC-006: LiteLLM chat — llama3
- **Layer:** LiteLLM
- **Priority:** P0
- **Preconditions:** TC-005 pass
- **Procedure:**
  1. ```bash
     curl -sS --max-time 90 -X POST http://127.0.0.1:4000/v1/chat/completions \
       -H "Authorization: Bearer ${LITELLM_MASTER_KEY:-admin}" \
       -H 'Content-Type: application/json' \
       -d '{"model":"llama3","messages":[{"role":"user","content":"Reply with exactly: OK"}],"max_tokens":32}'
     ```
- **Expected result:** HTTP 200; `choices[0].message.content` contains `OK`
- **Validation:** Non-empty `content`; status 200
- **Failure triage:** 502/503 → Ollama down; empty content → increase `max_tokens`
- **Last run (2026-07-19):** **PASS** — ~2.9 s

---

### TC-007: LiteLLM chat — hermes3
- **Layer:** LiteLLM
- **Priority:** P1
- **Preconditions:** TC-005 pass; `hermes3:8b` in Ollama
- **Procedure:** Same as TC-006 with `"model":"hermes3"` and prompt `"Say hi in one word"`
- **Expected result:** HTTP 200; non-empty greeting in `content`
- **Validation:** `choices[0].message.content` length &gt; 0
- **Failure triage:** Model mapping error → verify `ollama/hermes3:8b` in `litellm_config.yaml`
- **Last run (2026-07-19):** **PASS** — ~4.7 s

---

### TC-008: LiteLLM chat — deepseek-ocr (text smoke)
- **Layer:** LiteLLM
- **Priority:** P0
- **Preconditions:** TC-005 pass; `deepseek-ocr` pulled in Ollama
- **Procedure:**
  1. ```bash
     curl -sS --max-time 120 -X POST http://127.0.0.1:4000/v1/chat/completions \
       -H "Authorization: Bearer ${LITELLM_MASTER_KEY:-admin}" \
       -H 'Content-Type: application/json' \
       -d '{"model":"deepseek-ocr","messages":[{"role":"user","content":"Extract text from: HELLO OCR TEST"}],"max_tokens":64}'
     ```
- **Expected result:** HTTP 200; `content` references OCR input or extracted text
- **Validation:** Non-empty `content`; no 5xx
- **Failure triage:** Timeout → cold model load; 500 → check Ollama logs
- **Last run (2026-07-19):** **PASS** — ~4.0 s

---

### TC-009: LiteLLM chat — qwen3-vl text
- **Layer:** LiteLLM
- **Priority:** P0
- **Preconditions:** TC-005 pass; config uses `ollama_chat/qwen3-vl` (not `ollama/qwen3-vl`)
- **Procedure:**
  1. ```bash
     curl -sS --max-time 120 -X POST http://127.0.0.1:4000/v1/chat/completions \
       -H "Authorization: Bearer ${LITELLM_MASTER_KEY:-admin}" \
       -H 'Content-Type: application/json' \
       -d '{"model":"qwen3-vl","messages":[{"role":"user","content":"Reply OK only"}],"max_tokens":500}'
     ```
- **Expected result:** HTTP 200; `choices[0].message.content` non-empty (e.g. `OK`)
- **Validation:** Prefer `content` over `reasoning_content`; with `max_tokens` ≥ 500 expect visible answer
- **Failure triage:** Empty `content` with only `reasoning_content` → increase `max_tokens`; do **not** set `agent.reasoning_effort: none` in Hermes config; verify `ollama_chat` provider
- **Last run (2026-07-19):** **DEGRADED** — HTTP 200 but empty `content` (reasoning-only) at `max_tokens=8`; use 500+ for smoke

---

### TC-010: Hermes Gateway launchd status
- **Layer:** Hermes Gateway
- **Priority:** P0
- **Preconditions:** Gateway installed at `~/.hermes/hermes-agent/`; launchd plist loaded
- **Procedure:**
  1. `launchctl list | grep ai.hermes.gateway`
  2. `hermes gateway status`
  3. `tail -20 ~/.hermes/logs/gateway.log`
- **Expected result:** launchd shows running PID; CLI status OK; log contains `Telegram connected` (or recent activity)
- **Validation:** Non-zero PID; no repeated `APIConnectionError` to `:4000` in `~/.hermes/logs/errors.log`
- **Failure triage:** LiteLLM down → fix TC-004 first; restart → `hermes gateway restart`
- **Last run (2026-07-19):** **PASS** — PID 2148, Telegram connected

---

### TC-011: Hermes Gateway LiteLLM config alignment
- **Layer:** Hermes Gateway
- **Priority:** P0
- **Preconditions:** `~/.hermes/config.yaml` readable
- **Procedure:**
  1. ```bash
     grep -A5 'custom_providers\|model:' ~/.hermes/config.yaml | head -20
     ```
  2. Confirm `model.provider: custom:litellm`, `base_url: http://127.0.0.1:4000/v1`, `key_env: LITELLM_MASTER_KEY`
  3. Confirm `model.default: qwen3-vl` (or documented override)
- **Expected result:** Provider points to LiteLLM, not direct Ollama
- **Validation:** `base_url` contains `:4000/v1`; rollback file exists at `config.workingwithoutLiteLLM.yaml`
- **Failure triage:** Wrong URL → edit config and `hermes gateway restart`
- **Last run (2026-07-19):** **PASS**

---

### TC-012: n8n container running
- **Layer:** n8n
- **Priority:** P0
- **Preconditions:** Docker running; container `n8n` created with restart policy
- **Procedure:**
  1. `docker ps --filter name=n8n --format '{{.Names}} {{.Status}}'`
  2. `curl -sS -o /dev/null -w 'HTTP:%{http_code}\n' http://127.0.0.1:5678/healthz`
  3. `curl -sS http://127.0.0.1:5678/healthz`
- **Expected result:** Container **Up**; healthz HTTP 200; body `{"status":"ok"}`
- **Validation:** Port 5678 listening; JSON status ok
- **Failure triage:** Stopped → `docker start n8n`; auto-restart → `docker update --restart unless-stopped n8n`
- **Last run (2026-07-19):** **PASS** — Up ~6 h

---

### TC-013: n8n stack-health webhook
- **Layer:** n8n
- **Priority:** P0
- **Preconditions:** TC-012 pass; workflow **Stack Health Check (Hermes)** active (deploy script above)
- **Procedure:**
  1. `curl -sS -w "\nHTTP:%{http_code}\n" http://127.0.0.1:5678/webhook/stack-health`
  2. Parse JSON for `ok`, `litellm`, `ollama`, `n8n` sections
- **Expected result:** HTTP 200; top-level `"ok": true`; LiteLLM health `"I'm alive!"`; Ollama model count &gt; 0
- **Validation:** `ok == true`; `litellm.models.count >= 4`; latency typically &lt; 500 ms (no LLM)
- **Failure triage:** 404 → redeploy health workflow; `host.docker.internal` failures → ensure LiteLLM/Ollama reachable from n8n container
- **Last run (2026-07-19):** **PASS** — ~48 ms

---

### TC-014: n8n hermes-llm-task webhook (summary)
- **Layer:** n8n
- **Priority:** P0
- **Preconditions:** TC-012 pass; **Hermes LLM Task Template (LiteLLM)** active
- **Procedure:**
  1. ```bash
     curl -sS --max-time 120 -X POST http://127.0.0.1:5678/webhook/hermes-llm-task \
       -H 'Content-Type: application/json' \
       -d '{"task":"Summarize in one sentence: Hermes E2E test run."}'
     ```
- **Expected result:** HTTP 200; JSON includes LLM summary text routed via LiteLLM (`llama3` default)
- **Validation:** Response contains non-empty summary; total latency typically 2–10 s
- **Failure triage:** 404 → run `create-n8n-llm-template-workflow.py`; 500 from LiteLLM → fix TC-004/006
- **Last run (2026-07-19):** **PASS** — ~3.9 s via llama3

---

### TC-015: Hermes Switch web panel
- **Layer:** Hermes Switch
- **Priority:** P1
- **Preconditions:** `Hermes_Switch/` present; Python 3 available
- **Procedure:**
  1. `/Users/shailja/clawd/Hermes_Switch/open-panel.sh`
  2. `curl -sS http://127.0.0.1:9120/api/status | python3 -m json.tool`
  3. Open `http://127.0.0.1:9120/` — verify UI title **Hermes Switch** and service rows
- **Expected result:** `/api/status` HTTP 200 with JSON array of services (`ollama`, `postgres`, `litellm`, `gateway`, `n8n`); each has `name`, `running`, `detail`
- **Validation:** JSON parse OK; at least 5 services listed; UI loads (not empty body)
- **Failure triage:** Empty `/` → restart via `open-panel.sh`; 404 on `/health` is expected (use `/api/status`); missing repo → `git checkout 2026-06-03-2cg9 -- Hermes_Switch/`
- **Last run (2026-07-19):** **DEGRADED** — listener up but `/health` 404, `/` empty; repo path missing on disk

---

### TC-016: Hermes Switch stackctl start/stop
- **Layer:** Hermes Switch
- **Priority:** P1
- **Preconditions:** TC-015 scripts executable; user accepts brief service interruption for stop test
- **Procedure:**
  1. `/Users/shailja/clawd/Hermes_Switch/stackctl.sh status | python3 -m json.tool`
  2. `./Hermes_Switch/stackctl.sh stop gateway` (optional isolated test)
  3. `./Hermes_Switch/stackctl.sh start gateway`
  4. Re-run status — gateway `running: true`
- **Expected result:** CLI emits valid JSON; start/stop changes `running` flags within ~30 s
- **Validation:** `hermes gateway status` matches Switch gateway row; master `start all` brings up LiteLLM + Gateway + n8n
- **Failure triage:** Permission errors on launchd → run from user GUI session; Docker errors → check Docker Desktop
- **Last run (2026-07-19):** Not executed (Switch repo degraded)

---

### TC-017: Neo4j docker compose health
- **Layer:** Neo4j
- **Priority:** P1
- **Preconditions:** `cd neo4j && docker compose up -d`
- **Procedure:**
  1. `docker ps --filter name=neo4j --format '{{.Status}}'`
  2. `curl -sS -o /dev/null -w 'HTTP:%{http_code}\n' http://127.0.0.1:7474`
  3. `docker exec neo4j cypher-shell -u neo4j -p neo4j_local_dev 'RETURN 1 AS n;'`
- **Expected result:** Container **healthy**; Browser HTTP 200; Cypher returns `n = 1`
- **Validation:** Health check green; cypher-shell exit 0
- **Failure triage:** Auth failure → use password from `neo4j/docker-compose.yml` (`neo4j_local_dev`); slow start → wait 30 s after `up -d`
- **Last run (2026-07-19):** **PASS** — v5.26.28, ~15 ms browser

---

### TC-018: GraphRAG knowledge app / query smoke
- **Layer:** GraphRAG
- **Priority:** P2
- **Preconditions:** Neo4j TC-017 pass; `knowledge/` venv + ingested corpus (see `knowledge/TESTING_AND_TUNING.md` on `pr/graphrag-knowledge`)
- **Procedure:**
  1. ```bash
     cd /Users/shailja/clawd/knowledge && source .venv/bin/activate
     python -c "from vector_query import chunk_count; print('chunks:', chunk_count())"
     ```
  2. ```bash
     python -c "
     from hybrid_retriever import retrieve
     from grounded_answer import answer_question
     r = retrieve('What is federated learning?', top_k=3)
     print(answer_question('What is federated learning?', r)[:200])
     "
     ```
  3. Optional UI: `streamlit run app.py` → ask one question in browser
- **Expected result:** `chunk_count > 0`; hybrid query returns grounded answer with citations
- **Validation:** No import errors; answer references known `paper_id` slugs
- **Failure triage:** Empty Chroma → re-run ingest; Neo4j empty → `neo4j/whitepapers/health_check.py`; missing code → checkout `pr/graphrag-knowledge`
- **Last run (2026-07-19):** **SKIP** — `knowledge/` had no `app.py` / service on disk (only `.venv`)

---

## Integration tests

### TC-019: n8n → LiteLLM → Ollama path
- **Layer:** Integration
- **Priority:** P0
- **Preconditions:** TC-013 and TC-014 pass
- **Procedure:**
  1. Run TC-013 (`stack-health`) — confirms n8n reaches LiteLLM + Ollama from inside Docker
  2. Run TC-014 (`hermes-llm-task`) — confirms n8n POST reaches LiteLLM chat → Ollama inference
  3. Optional: `hermes mcp test n8n` — MCP connectivity from Gateway
- **Expected result:** Both webhooks HTTP 200; stack-health `ok: true`; llm-task returns model output
- **Validation:** End-to-end without manual curl to Ollama from host for llm-task path
- **Failure triage:** `host.docker.internal` → Docker Desktop networking; LiteLLM auth → Bearer key in workflow matches `LITELLM_MASTER_KEY`
- **Last run (2026-07-19):** **PASS**

---

### TC-020: Hermes config model names ↔ LiteLLM registry
- **Layer:** Integration
- **Priority:** P0
- **Preconditions:** TC-005 and TC-011 pass
- **Procedure:**
  1. List LiteLLM models (TC-005)
  2. Read Hermes defaults: `grep -E 'default:|model:' ~/.hermes/config.yaml`
  3. Compare: Hermes `qwen3-vl` must exist in LiteLLM registry; OCR/vision aliases match `litellm_config.yaml`
- **Expected result:** `{qwen3-vl, deepseek-ocr, hermes3, llama3}` aligned across both configs
- **Validation:** Set intersection equals expected four models
- **Failure triage:** Rename drift → update both files; restart LiteLLM + Gateway
- **Last run (2026-07-19):** **PASS**

---

### TC-021: Telegram → Hermes → LiteLLM → Ollama (OCR flow)
- **Layer:** Integration
- **Priority:** P0
- **Preconditions:** TC-010 pass; authorized Telegram user; bot `@DhauladharBot`
- **Procedure:**
  1. In Telegram DM: `/reset`
  2. Send a clear photo or screenshot with visible text
  3. Optional text: `"Extract all text from this image"`
  4. Monitor: `tail -f ~/.hermes/logs/gateway.log`
- **Expected result:** Gateway log shows `Image routing: native (model supports vision)`; bot replies with extracted text within 30–120 s
- **Validation:** Non-empty Telegram reply; no `Model provider failed after retries`; LiteLLM receives vision payload (`ollama_chat` path)
- **Failure triage:** Empty reply → TC-009/025 (qwen3-vl vision); LiteLLM down → TC-004; wrong user → check `TELEGRAM_ALLOWED_USERS`
- **Last run (2026-07-19):** Gateway runtime **PASS**; full bot round-trip not executed in automated run

---

## End-to-end workflow tests

### TC-022: Stack health full pass
- **Layer:** E2E
- **Priority:** P0
- **Preconditions:** Full stack up (Ollama, Postgres, LiteLLM, Gateway, n8n)
- **Procedure:**
  1. Run [Quick smoke script](#quick-smoke-script)
  2. Run TC-013 (`stack-health`)
  3. Run TC-010 (gateway + Telegram log line)
  4. Record pass/fail matrix → update `docs/E2E_TEST_RESULTS.md`
- **Expected result:** All P0 layers PASS; documented timestamp
- **Validation:** Matrix matches smoke + webhook + launchd checks
- **Failure triage:** See per-layer TC failure sections; fix lowest failing layer first (Ollama → Postgres → LiteLLM → Gateway → n8n)
- **Last run (2026-07-19):** **PARTIAL PASS** — core path healthy; Switch + GraphRAG degraded/skipped

---

### TC-023: OCR via LiteLLM (deepseek-ocr)
- **Layer:** E2E
- **Priority:** P0
- **Preconditions:** TC-008 pass
- **Procedure:**
  1. **Direct API:** TC-008 curl with OCR prompt
  2. **Via n8n:** ```bash
     curl -sS --max-time 120 -X POST http://127.0.0.1:5678/webhook/hermes-llm-task \
       -H 'Content-Type: application/json' \
       -d '{"task":"ocr","text":"Extract all visible text","image_url":"data:image/png;base64,<BASE64_PNG>"}'
     ```
  3. **Via Telegram:** send image to `@DhauladharBot` (may use qwen3-vl default — note model difference)
- **Expected result:** Non-empty extracted text from API paths; n8n returns OCR payload
- **Validation:** HTTP 200; `content` or workflow output length &gt; 10 chars for real images
- **Failure triage:** Use `deepseek-ocr` explicitly for OCR-specific path; vision URL must be data URL or HTTPS
- **Last run (2026-07-19):** **PASS** (direct LiteLLM + n8n llama3 summary path); dedicated OCR webhook not separately timed

---

### TC-024: Vision via LiteLLM (qwen3-vl)
- **Layer:** E2E
- **Priority:** P0
- **Preconditions:** TC-005 pass; `ollama_chat/qwen3-vl` in config; Pillow installed in LiteLLM venv
- **Procedure:**
  1. ```bash
     # 1×1 red PNG (minimal vision smoke)
     PNG='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
     curl -sS --max-time 120 -X POST http://127.0.0.1:4000/v1/chat/completions \
       -H "Authorization: Bearer ${LITELLM_MASTER_KEY:-admin}" \
       -H 'Content-Type: application/json' \
       -d "{\"model\":\"qwen3-vl\",\"messages\":[{\"role\":\"user\",\"content\":[
         {\"type\":\"text\",\"text\":\"What color is this image? One word.\"},
         {\"type\":\"image_url\",\"image_url\":{\"url\":\"data:image/png;base64,${PNG}\"}}
       ]}],\"max_tokens\":500}"
     ```
  2. Check Ollama: `ollama ps` during request
- **Expected result:** HTTP 200; `content` describes image (e.g. color name)
- **Validation:** Non-empty `content`; no Ollama runner crash
- **Failure triage:** HTTP 500 + "model runner stopped" → VRAM/model reload (`ollama stop qwen3-vl && ollama run qwen3-vl`); empty content → `max_tokens` 500+, `ollama_chat` provider; see [HERMES_AGENT_TELEGRAM_OLLAMA.md](./HERMES_AGENT_TELEGRAM_OLLAMA.md) troubleshooting
- **Last run (2026-07-19):** **FAIL** — HTTP 500, Ollama chat runner stopped (~5.1 s)

---

### TC-025: Kush file list (optional — LLM vs fast path)
- **Layer:** E2E
- **Priority:** P2
- **Preconditions:** Gateway running; `terminal.cwd` → `/Users/shailja/Documents/Kush`; `kush-file-share` skill enabled
- **Procedure:**
  1. **Slow path (LLM + tools):** In Telegram, send `"List files in my Kush folder"` — expect 5–30+ s via qwen3-vl tool routing
  2. **Fast path (deterministic — if implemented):** `/list` or `/share <filename>` quick commands — expect &lt; 500 ms
  3. **Local verify (no Telegram):**
     ```bash
     ls -la /Users/shailja/Documents/Kush | head -20
     test -f /Users/shailja/Documents/Kush/.hermes.md && echo OK marker
     ```
  4. Check gateway log for `search_files` or quick-command handler
- **Expected result:** Slow path returns directory listing; fast path (when deployed) bypasses LLM
- **Validation:** Listing includes known folders (`P_Project/`, `Personal/`, etc.); file share attaches paths under Kush root
- **Failure triage:** Slow → implement `quick_commands` / separate file bot; permission denied → `gateway.media_delivery_allow_dirs`; wrong cwd → fix `terminal.cwd` in config
- **Last run (2026-07-19):** Config **OK**; fast `/list` **not implemented**; LLM path works but slow (~5–30 s)

---

## Test case index

| ID | Title | Layer | Priority |
|----|-------|-------|----------|
| TC-001 | Ollama API tags | Ollama | P0 |
| TC-002 | Ollama direct generate | Ollama | P1 |
| TC-003 | Postgres LiteLLM DB | Postgres | P0 |
| TC-004 | LiteLLM liveliness | LiteLLM | P0 |
| TC-005 | LiteLLM model registry | LiteLLM | P0 |
| TC-006 | LiteLLM chat llama3 | LiteLLM | P0 |
| TC-007 | LiteLLM chat hermes3 | LiteLLM | P1 |
| TC-008 | LiteLLM chat deepseek-ocr | LiteLLM | P0 |
| TC-009 | LiteLLM chat qwen3-vl text | LiteLLM | P0 |
| TC-010 | Gateway launchd status | Hermes Gateway | P0 |
| TC-011 | Gateway LiteLLM config | Hermes Gateway | P0 |
| TC-012 | n8n container | n8n | P0 |
| TC-013 | n8n stack-health webhook | n8n | P0 |
| TC-014 | n8n hermes-llm-task webhook | n8n | P0 |
| TC-015 | Hermes Switch panel | Hermes Switch | P1 |
| TC-016 | Hermes Switch stackctl | Hermes Switch | P1 |
| TC-017 | Neo4j health | Neo4j | P1 |
| TC-018 | GraphRAG smoke | GraphRAG | P2 |
| TC-019 | n8n → LiteLLM → Ollama | Integration | P0 |
| TC-020 | Config ↔ registry match | Integration | P0 |
| TC-021 | Telegram OCR flow | Integration | P0 |
| TC-022 | Stack health full pass | E2E | P0 |
| TC-023 | OCR via LiteLLM | E2E | P0 |
| TC-024 | Vision via qwen3-vl | E2E | P0 |
| TC-025 | Kush file list | E2E | P2 |

**Total test cases: 25**

---

## Latest run summary (from E2E_TEST_RESULTS.md)

| Layer | Result | Notes |
|-------|--------|-------|
| Ollama | PASS | 8 models |
| Postgres | PASS | healthy |
| LiteLLM | PASS (vision FAIL) | qwen3-vl text degraded at low max_tokens |
| Hermes Gateway | PASS | Telegram connected |
| n8n | PASS | both webhooks OK |
| Hermes Switch | DEGRADED | repo missing; stale `:9120` process |
| Neo4j | PASS | healthy |
| GraphRAG | SKIP | service not deployed |

See full details, latencies, and blockers: **[E2E_TEST_RESULTS.md](./E2E_TEST_RESULTS.md)**

---

## Related documentation

- [HERMES_AGENT_TELEGRAM_OLLAMA.md](./HERMES_AGENT_TELEGRAM_OLLAMA.md) — architecture, ops, qwen3-vl troubleshooting
- [E2E_TEST_RESULTS.md](./E2E_TEST_RESULTS.md) — latest automated run (2026-07-19)
- `knowledge/TESTING_AND_TUNING.md` — GraphRAG evaluation (branch `pr/graphrag-knowledge`)
- `neo4j/README.md` — Neo4j local setup
- `Hermes_Switch/README.md` — Switch panel (branch `2026-06-03-2cg9`)
