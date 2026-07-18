# GraphRAG Hybrid — Whitepaper Knowledge System

Neo4j knowledge graph + Chroma vector search + Streamlit Q&A.

## Prerequisites

- Neo4j running (`cd ../neo4j && docker compose up -d`)
- Ollama running with `nomic-embed-text` and `qwen2.5:7b`
- Graph already ingested (`neo4j/whitepapers/ingest.py`)

## Setup

```bash
cd /Users/shailja/clawd/knowledge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Ingest vectors (GraphRAG Phase 2)

Graph is already loaded. Embed passages into Chroma:

```bash
# All PDFs
python ingest_all.py --vectors-only

# Single paper
python ingest_all.py --vectors-only --paper TelcoGPT.pdf

# Full rebuild (graph + vectors)
python ingest_all.py --reset-graph --reset-vectors
```

## Streamlit UI

```bash
streamlit run app.py
# → http://localhost:8501
```

### Tabs

| Tab | Purpose |
|-----|---------|
| **Overview** | Graph stats, papers, concept bridges |
| **Graph Explorer** | Search concepts → papers |
| **Semantic Search** | Chroma passage search |
| **Ask (GraphRAG)** | Hybrid Q&A with grounded answer |

## CLI testing

```python
from hybrid_retriever import retrieve
from grounded_answer import answer_question

print(retrieve("O-RAN AI/ML use cases"))
print(answer_question("What is TelcoGPT's approach to telco language?")["answer"])
```

## Architecture

```
PDF → extract_pdf → ┬→ Neo4j (graph: concepts, citations)
                    └→ Chroma (vectors: passages)

Question → graph filter (paper_ids) → vector search → Ollama answer
```

## Config

See `.env.example` — key vars:

- `CHROMA_PATH` — `../rag/chroma_db`
- `CHROMA_COLLECTION` — `whitepaper_chunks`
- `EMBED_CHUNK_CHARS` — 1000 (retrieval chunks)
- `EMBED_MAX_CHARS` — 6000 (Ollama embed limit; overlap can grow chunks)
- `OLLAMA_CHAT_MODEL` — `qwen2.5:7b`

## Related

- **[TESTING_AND_TUNING.md](TESTING_AND_TUNING.md)** — how to test, evaluate, and tune GraphRAG
- [neo4j/whitepapers/](../neo4j/whitepapers/) — graph ingest pipeline
- Notion: Neo4J - KG - GraphRAG
