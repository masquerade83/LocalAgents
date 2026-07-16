"""Configuration for whitepaper knowledge graph ingestion."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_MODULE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _MODULE_DIR.parent.parent

load_dotenv(_MODULE_DIR / ".env")


def _resolve_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (_REPO_ROOT / path).resolve()
    return path


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j_local_dev")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "300"))

WHITEPAPERS_PATH = _resolve_path(
    os.getenv("WHITEPAPERS_PATH", str(_REPO_ROOT / "whitepapers"))
)
CACHE_DIR = _MODULE_DIR / ".cache"
SCHEMA_PATH = _MODULE_DIR / "schema.cypher"

RAG_CHUNK_CHARS = int(os.getenv("RAG_CHUNK_CHARS", "6000"))
