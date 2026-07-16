"""Hybrid graph-filtered vector retrieval."""

from __future__ import annotations

import re
from typing import Any

from config import GRAPH_CONCEPT_LIMIT, VECTOR_TOP_K
from graph_query import GraphQuery
from vector_query import search


def extract_keywords(question: str) -> list[str]:
    stop = {
        "the", "a", "an", "and", "or", "what", "which", "how", "does", "do",
        "is", "are", "in", "on", "for", "to", "of", "with", "about", "papers",
        "paper", "mention", "mentions", "compare", "between", "from",
    }
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-/+]{1,}", question)
    keywords = [t for t in tokens if t.lower() not in stop and len(t) > 2]
    return keywords[:GRAPH_CONCEPT_LIMIT]


def retrieve(
    question: str,
    *,
    paper_ids: list[str] | None = None,
    use_graph_filter: bool = True,
    top_k: int = VECTOR_TOP_K,
) -> dict[str, Any]:
    keywords = extract_keywords(question)
    graph_paper_ids: list[str] = []
    graph_context = ""
    matched_concepts: list[str] = []

    with GraphQuery() as gq:
        if use_graph_filter and not paper_ids:
            for kw in keywords:
                matched_concepts.extend(gq.search_concepts(kw, limit=3))
            matched_concepts = list(dict.fromkeys(matched_concepts))[:GRAPH_CONCEPT_LIMIT]
            graph_paper_ids = gq.paper_ids_for_keywords(keywords or matched_concepts)

        filter_ids = paper_ids or graph_paper_ids or None
        if filter_ids:
            graph_context = gq.graph_context_for_papers(filter_ids[:10])

    hits = search(question, top_k=top_k, paper_ids=filter_ids)

    # Fallback: if graph filter returned nothing useful, search all papers
    if not hits and filter_ids:
        hits = search(question, top_k=top_k, paper_ids=None)

    return {
        "question": question,
        "keywords": keywords,
        "matched_concepts": matched_concepts,
        "paper_filter": filter_ids,
        "graph_context": graph_context,
        "passages": hits,
    }
