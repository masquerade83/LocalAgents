"""Embed whitepaper PDF chunks into Chroma via Ollama."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb
import httpx

from config import (
    CHROMA_COLLECTION,
    CHROMA_PATH,
    CHUNK_OVERLAP,
    EMBED_CHUNK_CHARS,
    EMBED_MAX_CHARS,
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    OLLAMA_TIMEOUT,
    WHITEPAPERS_PATH,
)
from extract_pdf import chunk_section_text, extract_pdf

logger = logging.getLogger(__name__)


def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    payload = {"model": OLLAMA_EMBED_MODEL, "input": texts}
    with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
        response = client.post(f"{OLLAMA_BASE_URL}/api/embed", json=payload)
        response.raise_for_status()
        data = response.json()
    return data.get("embeddings", [])


def embed_text_safe(text: str) -> list[float] | None:
    """Embed one passage; shrink on failure (Ollama rejects oversized inputs)."""
    for limit in (EMBED_MAX_CHARS, 4000, 2000, 1000):
        snippet = text[:limit].strip()
        if not snippet:
            return None
        try:
            return embed_texts([snippet])[0]
        except httpx.HTTPStatusError:
            continue
    logger.warning("Skipping unembeddable chunk (%s chars)", len(text))
    return None


def build_embed_chunks(paper: dict[str, Any], chunk_chars: int, overlap: int) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    paper_id = paper["paper_id"]
    paper_title = paper.get("title") or paper_id
    source_path = paper.get("source_path") or ""

    for section in paper.get("sections") or []:
        section_title = section.get("title", "Body")
        section_order = int(section.get("order", 0))
        section_text = section.get("text", "")
        if not section_text.strip():
            continue

        # Re-chunk smaller for retrieval, with overlap via sliding windows on paragraphs
        base_chunks = chunk_section_text(section_text, chunk_chars)
        for chunk_index, chunk_text in enumerate(base_chunks):
            if overlap and chunk_index > 0 and len(chunk_text) > overlap:
                prev_tail = base_chunks[chunk_index - 1][-overlap:]
                chunk_text = prev_tail + "\n\n" + chunk_text

            chunk_text = chunk_text[:EMBED_MAX_CHARS]

            chunk_id = f"{paper_id}::s{section_order}::c{chunk_index}::n{len(chunks)}"
            chunks.append(
                {
                    "id": chunk_id,
                    "text": chunk_text,
                    "metadata": {
                        "paper_id": paper_id,
                        "paper_title": paper_title,
                        "section_title": section_title,
                        "section_order": section_order,
                        "chunk_index": chunk_index,
                        "chunk_id": chunk_id,
                        "source_path": source_path,
                    },
                }
            )
    return chunks


def embed_paper(pdf_path: Path, *, chunk_chars: int = EMBED_CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> int:
    paper = extract_pdf(pdf_path, chunk_chars=chunk_chars * 3)  # larger sections first, then re-chunk
    embed_chunks = build_embed_chunks(paper, chunk_chars, overlap)
    if not embed_chunks:
        return 0

    collection = get_collection()
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    all_embeddings: list[list[float]] = []

    for chunk in embed_chunks:
        text = chunk["text"].strip()
        if not text:
            continue
        embedding = embed_text_safe(text)
        if embedding is None:
            continue
        ids.append(chunk["id"])
        documents.append(text[:EMBED_MAX_CHARS])
        metadatas.append(chunk["metadata"])
        all_embeddings.append(embedding)

    if not ids:
        return 0

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=all_embeddings)
    logger.info("Embedded %s chunks from %s", len(ids), pdf_path.name)
    return len(ids)


def embed_corpus(
    corpus_path: Path = WHITEPAPERS_PATH,
    *,
    single_paper: str | None = None,
    chunk_chars: int = EMBED_CHUNK_CHARS,
    overlap: int = CHUNK_OVERLAP,
) -> dict[str, int]:
    if single_paper:
        pdfs = [corpus_path / single_paper if not Path(single_paper).is_absolute() else Path(single_paper)]
    else:
        pdfs = sorted(corpus_path.rglob("*.pdf"))

    total_chunks = 0
    papers = 0
    for pdf in pdfs:
        if not pdf.exists():
            raise FileNotFoundError(pdf)
        total_chunks += embed_paper(pdf, chunk_chars=chunk_chars, overlap=overlap)
        papers += 1

    return {"papers": papers, "chunks": total_chunks}


def reset_collection() -> None:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        client.delete_collection(CHROMA_COLLECTION)
    except Exception:
        pass
    get_collection()
    logger.info("Reset Chroma collection %s", CHROMA_COLLECTION)
