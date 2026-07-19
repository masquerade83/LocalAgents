# Hermes Stack E2E Test Results

**Run timestamp:** 2026-07-19 02:20 IST  
**Workspace:** `/Users/shailja/clawd`  
**Tester:** automated (curl / Python / docker / launchctl)

## Executive summary

Core path **Ollama → LiteLLM → Router → Hermes/n8n** is **healthy** when router is started. **21 PASS**, **5 FAIL**, **3 SKIP**. Hermes Switch restored and **PASS**. **qwen3-vl vision** still **FAIL** (HTTP 500). **GraphRAG** not deployed. Router must be started manually (`router/run_router.sh`) — not launchd-managed; died mid-run during long LLM tests.

## Layer matrix

| Layer | Result | Latency / details |
|-------|--------|-------------------|
| **1. Ollama** | **PASS** | 8 models, ~12 ms |
| **2. Postgres** | **PASS** | `:5432` healthy; `SELECT 1` OK |
| **3. LiteLLM (:4000)** | **PASS** (vision **FAIL**) | Liveliness OK; llama3/hermes3/deepseek-ocr OK; qwen3-vl text OK at max_tokens=500; vision **HTTP 500** |
| **4. Model Router (:3999)** | **PASS*** | Health OK; text→hermes3; image→deepseek-ocr (*started manually; not persistent launchd*) |
| **5. Hermes Gateway** | **PASS** | launchd running; config points to `:3999/v1` |
| **6. n8n (:5678)** | **PASS** | stack-health + hermes-llm-task webhooks OK |
| **7. Hermes Switch (:9120)** | **PASS** | 6 services in `/api/status` |
| **8. Neo4j** | **PASS** | Browser :7474 OK |
| **9. GraphRAG** | **SKIP** | `knowledge/app.py` absent |

## Test case results

| ID | Test | Result | Notes |
|----|------|--------|-------|
| TC-001 | Ollama API tags | **PASS** | 8 models |
| TC-002 | Ollama direct generate | **PASS** | llama3 ~2.8s |
| TC-003 | Postgres | **PASS** | |
| TC-004 | LiteLLM liveliness | **PASS** | |
| TC-005 | LiteLLM model registry | **PASS** | 4 models |
| TC-006 | LiteLLM chat llama3 | **PASS** | ~209 ms |
| TC-007 | LiteLLM chat hermes3 | **PASS** | ~3.6 s |
| TC-008 | LiteLLM chat deepseek-ocr | **PASS** | ~6.5 s |
| TC-009 | LiteLLM chat qwen3-vl text | **PASS** | max_tokens=500 |
| TC-010 | Gateway launchd | **PASS** | |
| TC-011 | Gateway config → router | **PASS** | `:3999/v1` |
| TC-012 | n8n container | **PASS** | |
| TC-013 | stack-health webhook | **PASS** | ok=true |
| TC-014 | hermes-llm-task webhook | **PASS** | |
| TC-015 | Hermes Switch panel | **PASS** | 6 services |
| TC-016 | Hermes Switch stackctl | **PASS** | |
| TC-017 | Neo4j health | **PASS** | |
| TC-018 | GraphRAG smoke | **SKIP** | not deployed |
| TC-019 | n8n → LiteLLM → Ollama | **PASS** | |
| TC-020 | Config ↔ registry | **PASS** | |
| TC-021 | Telegram OCR flow | **SKIP** | manual |
| TC-022 | Stack health full pass | **PASS** | 6/6 P0 |
| TC-023 | OCR via LiteLLM | **PASS** | |
| TC-024 | Vision qwen3-vl | **FAIL** | HTTP 500 |
| TC-025 | Kush file list | **SKIP** | manual |
| TC-R01 | Router health | **PASS*** | after restart |
| TC-R02 | Router text route | **PASS*** | hermes3 |
| TC-R03 | Router short text | **PASS*** | llama3 |
| TC-R04 | Router image route | **PASS*** | deepseek-ocr |

## Blockers

1. **qwen3-vl vision** — Ollama runner crash on image input; inspect VRAM/logs
2. **Router persistence** — add launchd or Hermes Switch auto-start; router died during long test batch
3. **GraphRAG** — deploy `knowledge/` on `pr/graphrag-knowledge` branch
