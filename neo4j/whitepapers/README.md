# Whitepaper Knowledge Graph

Ingest local PDF whitepapers into Neo4j as a knowledge graph with **citation** and **concept** layers.

## Prerequisites

- Neo4j running: `cd ../ && docker compose up -d`
- Ollama running at `http://127.0.0.1:11434` (for LLM extraction)
- PDFs in the corpus folder (default: `../../whitepapers/`)

## Setup

```bash
cd /Users/shailja/clawd/neo4j/whitepapers
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional — defaults work with local Neo4j/Ollama
```

## Usage

```bash
# Apply schema only
python ingest.py --schema-only

# Ingest all PDFs in corpus folder
python ingest.py --path /Users/shailja/clawd/whitepapers

# Ingest one paper
python ingest.py --paper my-whitepaper.pdf

# Rebuild graph from scratch
python ingest.py --reset --path /Users/shailja/clawd/whitepapers

# PDF structure only (no Ollama) — useful for testing
python ingest.py --skip-llm

# Limit LLM section passes while testing
python ingest.py --max-sections 2
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `neo4j_local_dev` | Neo4j password |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama API |
| `OLLAMA_MODEL` | `llama3` | Model for extraction |
| `WHITEPAPERS_PATH` | `../../whitepapers` | PDF corpus folder |
| `RAG_CHUNK_CHARS` | `6000` | Section chunk size |

## Graph schema

### Nodes

| Label | Key | Properties |
|-------|-----|------------|
| `Paper` | `id` | `title`, `year`, `abstract`, `source_path`, `is_stub` |
| `Author` | `name` | — |
| `Concept` | `name` | `definition` |
| `Section` | `id` | `title`, `order` |

### Relationships

| Type | From → To |
|------|-----------|
| `AUTHORED` | Author → Paper |
| `CITES` | Paper → Paper |
| `MENTIONS` | Paper → Concept |
| `DEFINES` | Paper → Concept |
| `RELATED_TO` | Concept → Concept |
| `PART_OF` | Section → Paper |
| `APPEARS_IN` | Concept → Section |

Stub `Paper` nodes are created for cited works not yet in your corpus (`is_stub: true`).

## Validation queries

Open Neo4j Browser at http://localhost:7474 and run:

```cypher
// Overview counts
MATCH (p:Paper) RETURN count(p) AS papers;
MATCH (c:Concept) RETURN count(c) AS concepts;
MATCH ()-[r:CITES]->() RETURN count(r) AS citations;

// Papers with authors
MATCH (a:Author)-[:AUTHORED]->(p:Paper)
RETURN p.title, collect(a.name) AS authors
ORDER BY p.title;

// Cross-paper concept bridge
MATCH (p1:Paper)-[:MENTIONS]->(c:Concept)<-[:MENTIONS]-(p2:Paper)
WHERE p1 <> p2
RETURN c.name, p1.title AS paper1, p2.title AS paper2
LIMIT 20;

// Citation subgraph (1–2 hops)
MATCH path = (p:Paper)-[:CITES*1..2]->(q:Paper)
RETURN path LIMIT 25;

// Concepts defined by a paper
MATCH (p:Paper {id: 'your-paper-id'})-[:DEFINES]->(c:Concept)
RETURN c.name, c.definition;

// Find stub papers (cited but not yet ingested)
MATCH (p:Paper {is_stub: true})
RETURN p.title, p.year
ORDER BY p.title;
```

## Pipeline

```
PDF → extract_pdf.py → intermediate JSON (.cache/)
    → extract_graph.py (Ollama) → enriched JSON
    → load_neo4j.py (MERGE) → Neo4j graph
```

Re-running ingest on the same folder is idempotent — nodes are merged, not duplicated.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `No PDFs found` | Add `.pdf` files to `whitepapers/` or set `WHITEPAPERS_PATH` |
| Ollama connection error | Start Ollama; verify `curl http://127.0.0.1:11434/api/tags` |
| Neo4j auth error | Match credentials in `.env` to `neo4j/docker-compose.yml` |
| Slow ingest | Use `--max-sections 3` while testing; run full corpus overnight |
| Bad extractions | Re-run with `--refresh-cache` after prompt tweaks |

## Related

- [Neo4j Docker setup](../README.md)
- [RAG stack](../../rag/) — optional v2 hybrid search
