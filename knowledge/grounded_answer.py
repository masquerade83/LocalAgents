"""Grounded LLM answers from hybrid retrieval results."""

from __future__ import annotations

import httpx

from config import OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL, OLLAMA_TIMEOUT
from hybrid_retriever import retrieve


ANSWER_PROMPT = """You are a research assistant for telco/LLM whitepapers.

Answer ONLY using the graph context and source passages below.
If the answer is not supported by the sources, say "Not found in corpus."

Graph context:
{graph_context}

Source passages:
{passages}

Question: {question}

Respond with:
1. Answer (2-4 sentences)
2. Sources (paper title + section for each passage used)
3. Related concepts from graph (if any)
"""


def format_passages(passages: list[dict]) -> str:
    if not passages:
        return "(no passages retrieved)"
    blocks = []
    for i, p in enumerate(passages, 1):
        blocks.append(
            f"[{i}] Paper: {p.get('paper_title','?')} | Section: {p.get('section_title','?')}\n"
            f"{p.get('text','')[:1200]}"
        )
    return "\n\n".join(blocks)


def answer_question(
    question: str,
    *,
    paper_ids: list[str] | None = None,
    use_graph_filter: bool = True,
) -> dict:
    retrieval = retrieve(question, paper_ids=paper_ids, use_graph_filter=use_graph_filter)
    prompt = ANSWER_PROMPT.format(
        graph_context=retrieval.get("graph_context") or "(none)",
        passages=format_passages(retrieval.get("passages") or []),
        question=question,
    )

    payload = {
        "model": OLLAMA_CHAT_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }
    with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
        response = client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()

    return {
        "question": question,
        "answer": data.get("response", "").strip(),
        "retrieval": retrieval,
    }
