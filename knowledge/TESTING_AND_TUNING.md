# GraphRAG Testing, Evaluation & Tuning Guide

Complete guide for testing the whitepaper GraphRAG system, interpreting responses, measuring quality, and tuning for better performance.

**System:** Neo4j knowledge graph + Chroma vectors + Ollama (`qwen2.5:7b`)  
**Module:** `clawd/knowledge/`  
**Baseline eval:** `eval/test_questions.json` (2026-07-17)

---

## Table of contents

1. [Architecture recap](#1-architecture-recap)
2. [Prerequisites & health checks](#2-prerequisites--health-checks)
3. [How to test (layer by layer)](#3-how-to-test-layer-by-layer)
4. [Reading GraphRAG responses](#4-reading-graphrag-responses)
5. [Evaluation parameters](#5-evaluation-parameters)
6. [Baseline results (current corpus)](#6-baseline-results-current-corpus)
7. [Tuning knobs](#7-tuning-knobs)
8. [Tuning playbook (by symptom)](#8-tuning-playbook-by-symptom)
9. [Regression testing workflow](#9-regression-testing-workflow)
10. [Paper IDs reference](#10-paper-ids-reference)

---

## 1. Architecture recap

When you ask a question, three layers run in sequence:

```
Question
  → ① Keywords extracted
  → ② Neo4j graph filter (concept match → paper_ids → graph context)
  → ③ Chroma vector search (semantic passages, optionally filtered)
  → ④ Ollama chat (grounded answer from graph context + passages)
```

| Layer | Store / code | Role | LLM at query time? |
|-------|----------------|------|--------------------|
| Graph | Neo4j · `graph_query.py` | Which papers/concepts are structurally related | No |
| Vectors | Chroma · `vector_query.py` | Raw passage text (evidence) | No (embed only) |
| GraphRAG | `hybrid_retriever.py` + `grounded_answer.py` | Combine + synthesize answer | Yes |

**Link key:** `paper_id` (slug from PDF filename) — shared by Neo4j `Paper.id` and Chroma chunk metadata.

**Design principle:** Graph narrows scope → vectors find evidence → LLM answers with citations.

---

## 2. Prerequisites & health checks

### Start services

```bash
# Neo4j
cd /Users/shailja/clawd/neo4j && docker compose up -d

# GraphRAG venv
cd /Users/shailja/clawd/knowledge
source .venv/bin/activate
cp .env.example .env   # first time only
```

Verify Ollama: `curl -s http://127.0.0.1:11434/api/tags`

Required models: `qwen2.5:7b`, `nomic-embed-text`

### Graph health (Phase 1)

```bash
cd /Users/shailja/clawd/neo4j/whitepapers
source .venv/bin/activate
python health_check.py
```

| Metric | Expected (current corpus) | Red flag |
|--------|---------------------------|----------|
| Ingested papers | 6 | < 6 |
| Concepts | ~1,979 | Sudden drop after re-ingest |
| Citations | 13 | 0 on papers with bibliographies |
| Orphan concepts | 0 | > 0 |
| Noisy concepts (>60 chars) | ~10 | Growing over time |
| Low-concept papers | sample test only (9) | Real telco paper < 10 |

### Vector health (Phase 2)

```bash
cd /Users/shailja/clawd/knowledge && source .venv/bin/activate
python -c "from vector_query import chunk_count; print('chunks:', chunk_count())"
```

Expected: **882 chunks** in collection `whitepaper_chunks`.

If 0: run `python ingest_all.py --vectors-only`

### Launch Streamlit UI

```bash
streamlit run app.py
# → http://localhost:8501
```

---

## 3. How to test (layer by layer)

Test **bottom-up**: graph → vectors → hybrid Q&A. Each layer isolates one failure mode.

### 3.1 Layer A — Neo4j graph (no LLM at query time)

**Streamlit:** Tab **Graph Explorer**  
**Neo4j Browser:** http://localhost:7474 (`neo4j` / `neo4j_local_dev`)

| Test input | Pass criteria |
|------------|---------------|
| Keyword `O-RAN` | Returns concepts; lists OpenRAN Gym paper |
| Keyword `LLM` | Multiple concepts; several papers |
| Keyword `GPU` | GPU Accelerated 5G paper appears |

**Cypher gold questions:**

```cypher
// Papers mentioning O-RAN
MATCH (p:Paper)-[:MENTIONS]->(c:Concept)
WHERE NOT coalesce(p.is_stub, false)
  AND toLower(c.name) CONTAINS 'o-ran'
RETURN p.title, collect(c.name)[..5];

// Cross-paper LLM bridge
MATCH (p1:Paper)-[:MENTIONS]->(c:Concept)<-[:MENTIONS]-(p2:Paper)
WHERE p1 <> p2 AND toLower(c.name) CONTAINS 'llm'
RETURN c.name, p1.title, p2.title LIMIT 10;
```

**What this layer tells you:** Whether concept extraction was good enough for graph-assisted filtering.

---

### 3.2 Layer B — Vector retrieval (no graph filter)

**Streamlit:** Tab **Semantic Search** (leave paper_id filter empty)

| Question | Expected top paper | Baseline hit@3 |
|----------|-------------------|----------------|
| GPU acceleration in 5G RAN | `gpu-accelerated-5g-ran` | ✅ Hit (#1) |
| Telco-specific LLM problems | `telco-specific-llm-problems-techniques` | ✅ Hit (#1) |
| TelcoGPT approach | `telcogpt` | ❌ Miss (rank ~#7) |
| O-RAN AI/ML use cases | `o-ran-ai-ml-usecase` | ❌ Miss (rank ~#7) |
| Telecom language + LLMs | `telecom-language-through-llms` | ❌ Miss (not in top 8) |

**Read each result:**
- **`dist=`** — cosine distance; **lower = more similar**
- **Paper title / section** — provenance
- **Text** — exact evidence the LLM will see

**CLI inspection:**

```python
from vector_query import search
hits = search("What is TelcoGPT's approach?", top_k=8)
for i, h in enumerate(hits, 1):
    print(f"{i}. {h['paper_id']} dist={h['distance']:.3f}")
```

---

### 3.3 Layer C — Hybrid retrieval (graph + vectors)

**CLI:**

```python
from hybrid_retriever import retrieve

r = retrieve("What is TelcoGPT's approach?")
print("keywords:     ", r["keywords"])
print("concepts:     ", r["matched_concepts"])
print("paper_filter: ", r["paper_filter"])
for i, p in enumerate(r["passages"][:5], 1):
    print(f"  [{i}] {p['paper_id']} dist={p['distance']:.3f}")
```

**Compare hybrid vs vector-only:**

```python
r_h = retrieve(q, use_graph_filter=True)
r_v = retrieve(q, use_graph_filter=False)
print("Hybrid:  ", [p["paper_id"] for p in r_h["passages"][:5]])
print("Vector:  ", [p["paper_id"] for p in r_v["passages"][:5]])
```

**What to watch:**
- `paper_filter` — papers Neo4j scoped search to (can be too broad: 4–5 papers)
- `matched_concepts` — graph matches (may include noisy concepts like "CoT Approach")
- Fallback — if filter returns 0 hits, system searches full corpus automatically

---

### 3.4 Layer D — End-to-end Q&A

**Streamlit:** Tab **Ask (GraphRAG)**

Use gold questions from `eval/test_questions.json`:

1. Which papers mention O-RAN AI/ML use cases?
2. What is TelcoGPT's approach to building telecom-specific LLMs?
3. What GPU acceleration techniques are used in 5G RAN?
4. What are telco-specific LLM problems and techniques?
5. How can LLMs help understand telecom language?

**CLI:**

```python
from grounded_answer import answer_question
result = answer_question("What GPU acceleration techniques are used in 5G RAN?")
print(result["answer"])
```

**A/B tests in Streamlit Ask tab:**
- Toggle **Use graph pre-filter** on/off
- Set **paper_id** to lock scope (e.g. `telcogpt`)

---

## 4. Reading GraphRAG responses

A full Ask response has four parts:

```
┌──────────────────────────────────────────┐
│ 1. Answer (LLM synthesis)                │
├──────────────────────────────────────────┤
│ 2. Graph concepts: O-RAN, AI/ML, ...     │  ← Neo4j matches
│ 3. Paper filter: telcogpt, o-ran-...       │  ← Chroma scope
├──────────────────────────────────────────┤
│ 4. Source passages [1]–[8]               │  ← verify grounding here
└──────────────────────────────────────────┘
```

### How to verify grounding (manual)

For each claim in the answer:
1. Open the cited source passage expander
2. Confirm the claim appears in (or is directly implied by) that text
3. If not found → **hallucination** or **wrong passage ranked too low**

### Green flags

| Signal | Meaning |
|--------|---------|
| Answer uses specific terms from passages | Good retrieval + grounding |
| Sources cite correct paper + section | Metadata pipeline OK |
| Cross-paper mentions match graph bridges | Hybrid context helping |
| Latency ~4–6s | Normal for local Ollama |

### Red flags

| Signal | Likely cause |
|--------|--------------|
| Paper cited but not in corpus | LLM hallucination — tighten prompt |
| All 8 passages from one paper (survey) | Chunk dominance — needs per-paper dedup |
| Graph concepts unrelated to question | Noisy concept extraction |
| `paper_filter` lists 4+ papers for narrow Q | Graph filter too loose |
| "Not found in corpus" on known topic | Missing concept + weak vector match |

---

## 5. Evaluation parameters

Evaluate **three layers separately**, then end-to-end Q&A.

### 5.1 Graph extraction (Neo4j — offline / health check)

| Parameter | How to measure | Target |
|-----------|----------------|--------|
| Paper coverage | Ingested / PDFs in folder | 100% |
| Concepts per paper | `health_check.py` | Short: 20–50; survey: 200+ |
| Orphan concepts | Cypher count | 0 |
| Gold Cypher queries | `health_check.py` gold section | 5/5 pass |
| Citation count | vs bibliography spot-check | ≥ 50% recall (manual) |
| Concept precision | Sample 20 concepts vs PDF | ≥ 75% |

### 5.2 Vector retrieval

| Parameter | How to measure | Target | Current baseline |
|-----------|----------------|--------|------------------|
| **hit@3** | Expected `paper_id` in top 3 passages | ≥ 80% | **3/5 (60%)** |
| **hit@8** | Expected `paper_id` in top 8 | ≥ 90% | **4/5 (80%)** |
| MRR | 1/rank of first relevant chunk | ≥ 0.6 | ~0.4 (survey bias) |
| Passage relevance | Human 1–5 on top-5 chunks | ≥ 3.5 avg | Good for GPU/domain Qs |
| Query latency | Wall clock for `retrieve()` | < 1s | ~0.05–0.65s |

**hit@k algorithm:**

```python
def hit_at_k(passages, expected_substrings, k=3):
    for p in passages[:k]:
        pid = p.get("paper_id", "")
        if any(exp in pid for exp in expected_substrings):
            return True
    return False
```

### 5.3 Hybrid GraphRAG

| Parameter | How to measure | Target | Current baseline |
|-----------|----------------|--------|------------------|
| Graph filter precision | Filtered papers relevant to Q | High | Often over-broad |
| Hybrid vs vector-only | Compare top-5 paper_ids | Hybrid wins on cross-paper Qs | **Tie or vector wins** |
| End-to-end Q&A score | Rubric below | ≥ 6/8 per question | **5/5 pass** |
| Groundedness | Claims in source passages | ≥ 90% | ~100% (manual review) |
| Hallucination rate | Facts not in sources | ≤ 10% | 0% on gold set |
| Q&A latency | `answer_question()` | < 30s | ~4–6s |

### 5.4 Q&A scoring rubric (0–2 each, target ≥ 6/8)

| Dimension | 0 | 1 | 2 |
|-----------|---|---|---|
| **Correctness** | Wrong | Partially right | Accurate |
| **Grounded** | Invented facts | Some unsupported | All from sources |
| **Complete** | Misses main point | Main idea only | Covers nuance |
| **Source citation** | None | Vague | Paper + section named |

---

## 6. Baseline results (current corpus)

From eval run 2026-07-17 (`eval/test_questions.json`).

### Corpus stats

| Item | Value |
|------|-------|
| Papers | 6 ingested + 12 citation stubs |
| Concepts | 1,979 (post-cleanup) |
| Vector chunks | 882 |
| Survey paper chunks | 424 (48% of corpus) |

### Retrieval hit@3 (hybrid)

| Question | Expected paper | hit@3 |
|----------|----------------|-------|
| O-RAN AI/ML | `o-ran-ai-ml-usecase` | ❌ (rank ~#7) |
| TelcoGPT approach | `telcogpt` | ❌ (rank ~#7) |
| GPU 5G RAN | `gpu-accelerated-5g-ran` | ✅ (#1) |
| Telco LLM problems | `telco-specific-llm-problems-techniques` | ✅ (#1) |
| Telecom language | `telecom-language-through-llms` | ❌ (not in top 8) |

### Q&A scores

All 5 gold questions scored **8/8** on groundedness/correctness — LLM successfully used rank #7–8 passages even when hit@3 failed.

### Key finding

**Retrieval ranking is the bottleneck, not Q&A quality.** The LLM survey's 424 chunks dominate semantic search for broad telco/LLM questions.

---

## 7. Tuning knobs

### 7.1 GraphRAG query-time (`knowledge/.env`)

| Variable | Default | Effect | When to change |
|----------|---------|--------|----------------|
| `VECTOR_TOP_K` | 8 | Passages sent to LLM | ↑ if answers miss detail; ↓ for speed |
| `GRAPH_CONCEPT_LIMIT` | 5 | Max keywords/concepts for graph filter | ↓ if filter too broad |
| `OLLAMA_CHAT_MODEL` | `qwen2.5:7b` | Answer quality/speed | Try `hermes3:8b` for comparison |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Query embedding quality | Rarely change |
| `OLLAMA_TIMEOUT` | 300 | Per-request timeout | ↑ for slow hardware |

**Prompt tuning:** Edit `ANSWER_PROMPT` in `grounded_answer.py`
- Stricter grounding: add "Quote exact phrases from sources"
- Lower hallucination: set `temperature` to 0 in `answer_question()`
- Passage length: change `[:1200]` in `format_passages()`

**Graph filter tuning:** Edit `hybrid_retriever.py`
- Tighten filter: require 2+ keyword matches before filtering
- Disable filter: `use_graph_filter=False` (vector-only mode)

### 7.2 Vector ingest-time (`knowledge/.env`)

Requires re-embed: `python ingest_all.py --vectors-only --reset-vectors` (or reset collection first)

| Variable | Default | Effect | When to change |
|----------|---------|--------|----------------|
| `EMBED_CHUNK_CHARS` | 1000 | Retrieval chunk size | ↓ 800 for finer retrieval; ↑ 1500 for more context |
| `CHUNK_OVERLAP` | 200 | Boundary coverage | ↑ if answers miss cross-boundary facts |
| `EMBED_MAX_CHARS` | 6000 | Max chars per embed | Don't exceed Ollama embed limit |

### 7.3 Graph ingest-time (`neo4j/whitepapers/.env`)

Requires re-ingest: `python ingest.py --paper X.pdf --model qwen2.5:7b`

| Variable | Default | Effect | When to change |
|----------|---------|--------|----------------|
| `OLLAMA_MODEL` | llama3 | Extraction model | Use `qwen2.5:7b` (current best) |
| `RAG_CHUNK_CHARS` | 6000 | LLM extraction chunk size | ↓ for finer concept extraction |

**Post-ingest cleanup:** Always run `python cleanup_graph.py` after ingest.

---

## 8. Tuning playbook (by symptom)

### Symptom: Survey paper fills all top passages

**Cause:** 424/882 chunks from one paper; pure similarity ranking.

**Fixes (priority order):**
1. **Per-paper dedup** — cap chunks per `paper_id` in top-k (e.g. max 2) — *highest impact, not yet implemented*
2. Fetch `top_k * 3` candidates, then diversify before returning
3. MMR re-ranking to penalize redundant papers
4. Reduce survey chunk count ( larger `EMBED_CHUNK_CHARS` for that paper only — advanced)

---

### Symptom: Graph filter lists wrong papers

**Cause:** Keyword `CONTAINS` matches too many concepts (e.g. "LLM" matches everything).

**Fixes:**
1. Lower `GRAPH_CONCEPT_LIMIT` from 5 → 3
2. Require 2+ keyword hits in `paper_ids_for_keywords`
3. Use explicit `paper_ids=[...]` in Streamlit Ask tab
4. Turn off graph filter; rely on vector search only

---

### Symptom: Correct paper at rank #7, answer still OK

**Cause:** `VECTOR_TOP_K=8` saves Q&A even when hit@3 fails.

**Fixes:**
1. Implement per-paper dedup to promote rank #7 papers to top 3
2. Track hit@8 separately from hit@3 in eval
3. Don't reduce `VECTOR_TOP_K` below 8 until dedup is in place

---

### Symptom: Dedicated paper never appears (telecom-language)

**Cause:** Only 51 chunks vs survey's 424; always outranked.

**Fixes:**
1. Per-paper dedup (mandatory for fairness)
2. Ask with `paper_id=telecom-language-through-llms` filter
3. Add paper-specific metadata boost (advanced)

---

### Symptom: Hallucinated facts in answer

**Fixes:**
1. Set `temperature: 0` in `grounded_answer.py`
2. Strengthen prompt: "If not in sources, say Not found"
3. Verify source passages actually contain the claim
4. Reduce `VECTOR_TOP_K` if irrelevant passages confuse LLM

---

### Symptom: Missing concepts in graph explorer

**Fixes:**
1. Re-ingest paper with `qwen2.5:7b`
2. Smaller `RAG_CHUNK_CHARS` (4000) for extraction
3. Run `cleanup_graph.py` then `health_check.py`
4. Tune prompts in `neo4j/whitepapers/prompts.py`

---

### Symptom: Slow answers (>30s)

**Fixes:**
1. Use smaller chat model
2. Reduce `VECTOR_TOP_K`
3. Shorten passage truncation in `format_passages()`
4. Keep Ollama model warm (run a dummy query first)

---

## 9. Regression testing workflow

### Quick check (15 min)

```bash
# Graph
cd /Users/shailja/clawd/neo4j/whitepapers && source .venv/bin/activate
python health_check.py

# Vectors + spot Q&A
cd /Users/shailja/clawd/knowledge && source .venv/bin/activate
python -c "from vector_query import chunk_count; print(chunk_count())"
```

Then in Streamlit: run 5 gold questions in Ask tab; spot-check source passages.

### Full regression (after any tuning change)

```python
# save results back to eval/test_questions.json manually or via script
import json
from pathlib import Path
from hybrid_retriever import retrieve
from grounded_answer import answer_question

data = json.loads(Path("eval/test_questions.json").read_text())
for q in data["questions"]:
    r = retrieve(q["question"])
    hit3 = any(
        any(exp in p.get("paper_id","") for exp in q["expected_papers"])
        for p in r["passages"][:3]
    )
    print(f"{q['id']}: hit@3={hit3} filter={r.get('paper_filter')}")
```

### When to re-run full eval

| Change | Re-eval layers |
|--------|----------------|
| `.env` VECTOR_TOP_K / GRAPH_CONCEPT_LIMIT | Retrieval + Q&A |
| Re-embed (chunk size/overlap) | Vectors + Q&A |
| Re-ingest graph | Graph health + hybrid filter + Q&A |
| Prompt change in grounded_answer.py | Q&A only |
| Per-paper dedup implemented | Retrieval hit@3 (primary) |

### Scorecard template

| Layer | Metric | Before | After | Target |
|-------|--------|--------|-------|--------|
| Graph | Gold Cypher pass | 5/5 | | 5/5 |
| Graph | Orphan concepts | 0 | | 0 |
| Retrieval | hit@3 | 3/5 | | ≥ 4/5 |
| Retrieval | hit@8 | 4/5 | | 5/5 |
| Q&A | Avg score /8 | 8.0 | | ≥ 6.0 |
| Q&A | Hallucinations | 0 | | 0 |

---

## 10. Paper IDs reference

Use in Streamlit **paper_id filter** or CLI `paper_ids=[...]`.

| Paper | `paper_id` |
|-------|------------|
| TelcoGPT | `telcogpt` |
| O-RAN AI/ML Usecase | `o-ran-ai-ml-usecase` |
| GPU Accelerated 5G RAN | `gpu-accelerated-5g-ran` |
| LLM Survey | `large-language-model-llm-for-telecommunications-a-comprehensive-survey-on-principles-key-techniques-and-opportunities` |
| Telco LLM Problems | `telco-specific-llm-problems-techniques` |
| Telecom Language | `telecom-language-through-llms` |

List all IDs:

```bash
cd /Users/shailja/clawd/knowledge && source .venv/bin/activate
python -c "from graph_query import GraphQuery; g=GraphQuery(); [print(p['id']) for p in g.list_papers()]"
```

---

## Recommended next improvement

**Per-paper dedup in retrieval** — limit each paper to max 2 chunks in top-k. Addresses the #1 eval finding (survey chunk dominance). Expected impact: hit@3 from 3/5 → 4/5 or better without hurting Q&A quality.

---

## Related docs

- `README.md` — setup and architecture overview
- `eval/test_questions.json` — gold questions + baseline eval results
- `../neo4j/whitepapers/README.md` — graph ingest pipeline
- Notion: [Neo4J - KG - GraphRAG](https://app.notion.com/p/39f9eda1d5b3810b8332f7db1ce69d03)
