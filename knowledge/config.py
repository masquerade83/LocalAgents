"""Configuration for GraphRAG hybrid knowledge module."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_MODULE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _MODULE_DIR.parent
_WHITEPAPERS_MODULE = _REPO_ROOT / "neo4j" / "whitepapers"
WHITEPAPERS_MODULE_DIR = _WHITEPAPERS_MODULE

load_dotenv(_MODULE_DIR / ".env")

if str(_WHITEPAPERS_MODULE) not in sys.path:
    sys.path.insert(0, str(_WHITEPAPERS_MODULE))


def _resolve_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (_REPO_ROOT / path).resolve()
    return path


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j_local_dev")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "300"))

WHITEPAPERS_PATH = _resolve_path(
    os.getenv("WHITEPAPERS_PATH", str(_REPO_ROOT / "whitepapers"))
)
CHROMA_PATH = _resolve_path(os.getenv("CHROMA_PATH", str(_REPO_ROOT / "rag" / "chroma_db")))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "whitepaper_chunks")

EMBED_CHUNK_CHARS = int(os.getenv("EMBED_CHUNK_CHARS", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
EMBED_MAX_CHARS = int(os.getenv("EMBED_MAX_CHARS", "6000"))
VECTOR_TOP_K = int(os.getenv("VECTOR_TOP_K", "8"))
GRAPH_CONCEPT_LIMIT = int(os.getenv("GRAPH_CONCEPT_LIMIT", "5"))
