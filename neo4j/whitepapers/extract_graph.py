"""LLM-based entity and relationship extraction via Ollama."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT
from prompts import PAPER_METADATA_PROMPT, SECTION_CONCEPTS_PROMPT

logger = logging.getLogger(__name__)


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json_response(text: str) -> dict[str, Any]:
    cleaned = _strip_json_fence(text)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object from LLM")
    return payload


def call_ollama(prompt: str, model: str | None = None) -> str:
    model = model or OLLAMA_MODEL
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1},
    }
    with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
        response = client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
    return data.get("response", "")


def extract_paper_metadata(paper: dict[str, Any], model: str | None = None) -> dict[str, Any]:
    text = paper.get("full_text_preview") or ""
    if not text:
        sections = paper.get("sections") or []
        text = "\n\n".join(section.get("text", "") for section in sections[:3])

    prompt = PAPER_METADATA_PROMPT.format(title=paper.get("title", ""), text=text[:12000])
    raw = call_ollama(prompt, model=model)
    payload = _parse_json_response(raw)

    return {
        "title": payload.get("title") or paper.get("title"),
        "authors": payload.get("authors") or [],
        "year": payload.get("year") if payload.get("year") is not None else paper.get("year"),
        "abstract": payload.get("abstract") or paper.get("abstract") or "",
        "citations": payload.get("citations") or [],
    }


def extract_section_concepts(
    paper_title: str,
    section_title: str,
    section_text: str,
    model: str | None = None,
) -> list[dict[str, Any]]:
    prompt = SECTION_CONCEPTS_PROMPT.format(
        paper_title=paper_title,
        section_title=section_title,
        text=section_text[:10000],
    )
    raw = call_ollama(prompt, model=model)
    payload = _parse_json_response(raw)
    concepts = payload.get("concepts") or []
    if not isinstance(concepts, list):
        return []
    return [concept for concept in concepts if isinstance(concept, dict) and concept.get("name")]


def enrich_paper_with_graph(
    paper: dict[str, Any],
    model: str | None = None,
    max_sections: int | None = None,
) -> dict[str, Any]:
    metadata = extract_paper_metadata(paper, model=model)
    paper.update(
        {
            "title": metadata["title"],
            "authors": metadata["authors"],
            "year": metadata["year"],
            "abstract": metadata["abstract"],
            "citations": metadata["citations"],
        }
    )

    concepts_by_name: dict[str, dict[str, Any]] = {}
    sections = paper.get("sections") or []
    if max_sections is not None:
        sections = sections[:max_sections]

    for section in sections:
        section_title = section.get("title", "Body")
        section_text = section.get("text", "")
        if not section_text.strip():
            continue

        extracted = extract_section_concepts(
            paper_title=paper.get("title", ""),
            section_title=section_title,
            section_text=section_text,
            model=model,
        )

        for concept in extracted:
            name = str(concept.get("name", "")).strip()
            if not name:
                continue
            key = name.lower()
            existing = concepts_by_name.get(key, {"name": name, "definition": "", "defines": False, "related_to": [], "sections": []})
            definition = str(concept.get("definition") or "").strip()
            if definition and not existing.get("definition"):
                existing["definition"] = definition
            if concept.get("defines"):
                existing["defines"] = True
            related = concept.get("related_to") or []
            if isinstance(related, list):
                existing["related_to"] = sorted(set(existing.get("related_to", []) + [str(item) for item in related if item]))
            section_key = f"{section.get('order', 0)}::{section.get('chunk_index', 0)}"
            if section_key not in existing["sections"]:
                existing["sections"].append(section_key)
            concepts_by_name[key] = existing

    paper["concepts"] = list(concepts_by_name.values())
    return paper
