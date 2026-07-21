# Telco agent eval (ground truth)

Local golden set for validating Hermes → LiteLLM → Ollama (and n8n / LAN CP tool) responses.

## Layout

| Path | Purpose |
|------|---------|
| `golden.sample.jsonl` | Tiny schema examples (6 cases) |
| `golden.jsonl` | Full golden set with Hermes trace cases (12 cases) |
| `runs/` | Dated run outputs from scoring passes |

## Schema (one JSON object per line)

Required: `id`, `agent`, `input`, `context_refs`, `scoring_type`  
Optional: `expected_answer`, `expected_labels`, `expected_tools`, `rubric`, `tags`

`scoring_type`: `exact` | `fuzzy` | `label` | `tool` | `rubric` | `trace`

## How to grow the set (this box)

1. **Churn (~15)** — Pick 10 rows from IBM Telco Customer Churn. Emit exact Q&A (`MonthlyCharges`, `tenure`, `Contract`) and Yes/No `Churn` labels. Point `context_refs` at `customerID`.
2. **CSR (~15)** — From HF telecom support tickets: freeze `category` labels; hand-write 5 rubric references for open replies.
3. **QoE (~10)** — LAN CP `:8765` wifi/status tools, or a few NordicDat rows with a root-cause bucket.
4. **Traces (~5)** — Record real Hermes/n8n tool sequences once; store under `expected_tools` in order.

See the canvas: `telco-ground-truth-validation.canvas.tsx` (Cursor canvases folder).

## Scoring (minimal)

- **exact** — Normalize case/whitespace; numeric epsilon `0.01` for charges.
- **label** — Equality on `expected_labels` keys.
- **tool** — Required tool names present; args are a subset match.
- **rubric** — All `must` substrings/concepts present; none of `must_not`. Optional LLM-judge vs `rubric.reference` at temp `0` via LiteLLM — spot-check humans.
- **trace** — `expected_tools` as ordered subsequence, then final label/rubric check.

Do not treat LLM-as-judge as sole truth for credits, SLA promises, or fraud disposition.

## Run sketch

```bash
# Pseudocode — wire to Hermes chat or LiteLLM /v1/chat/completions
# for each line in golden.sample.jsonl:
#   response, tools = invoke_agent(case.input)
#   score = apply_scoring(case, response, tools)
#   append runs/$(date +%Y%m%d).jsonl
```

Prefer temperature `0` for factual/label cases. Keep stack smoke tests in `docs/HERMES_STACK_TEST_CASES.md`; this folder is for **answer / tool quality**, not service health.
