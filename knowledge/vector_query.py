"""Chroma vector search for whitepaper passages."""

from __future__ import annotations

from typing import Any

import httpx

from config import OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL, OLLAMA_TIMEOUT, VECTOR_TOP_K
from embed_chroma import get_collection


def embed_query(text: str) -> list[float]:
    payload = {"model": OLLAMA_EMBED_MODEL, "input": text}
    with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
        response = client.post(f"{OLLAMA_BASE_URL}/api/embed", json=payload)
        response.raise_for_status()
        data = response.json()
    embeddings = data.get("embeddings") or [[]]
    return embeddings[0]


def search(
    query: str,
    *,
    top_k: int = VECTOR_TOP_K,
    paper_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    collection = get_collection()
    if collection.count() == 0:
        return []

    query_embedding = embed_query(query)
    where = None
    if paper_ids:
        if len(paper_ids) == 1:
            where = {"paper_id": paper_ids[0]}
        else:
            where = {"paper_id": {"$in": paper_ids}}

    kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": min(top_k, max(collection.count(), 1)),
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)
    hits: list[dict[str, Any]] = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    for chunk_id, doc, meta, dist in zip(ids, docs, metas, dists):
        hits.append(
            {
                "chunk_id": chunk_id,
                "text": doc,
                "metadata": meta,
                "distance": dist,
                "paper_id": meta.get("paper_id"),
                "paper_title": meta.get("paper_title"),
                "section_title": meta.get("section_title"),
            }
        )
    return hits


def chunk_count() -> int:
    return get_collection().count()
