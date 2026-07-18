"""Concept validation, normalization, and deduplication for the whitepaper KG."""

from __future__ import annotations

import re

MAX_CONCEPT_LEN = 80

NOISE_PREFIX_RE = re.compile(r"^(?:positive|negative)\s+examples?\s*:", re.I)
CODE_ARTIFACT_RE = re.compile(
    r"^(?:iwl_|wrqu|tx_power|bsc_|rf_kill|device_id|device_status)|"
    r"^[a-z][a-z0-9]*_(?:dvm|get|set|power|data|mask|function)\b|"
    r"^[a-z_]{3,}$",
    re.I,
)
PAPER_TITLE_LIKE_RE = re.compile(
    r"^(?:[A-Z][a-z]+\s+){4,}.+(?:using|for|based on|network|model|learning)",
    re.I,
)

CANONICAL_ALIASES: dict[str, str] = {
    "llm": "Large Language Model",
    "llms": "Large Language Model",
    "large language model": "Large Language Model",
    "large language models": "Large Language Model",
    "large language models (llms)": "Large Language Model",
    "llm (large language model)": "Large Language Model",
    "telecom-specific llm": "Telecom-Specific LLM",
    "telecom specific llm": "Telecom-Specific LLM",
    "o-ran": "O-RAN",
    "openran": "O-RAN",
    "open ran": "O-RAN",
    "5g nr": "5G NR",
    "5g": "5G",
    "mimo": "MIMO",
    "lte": "LTE",
    "3gpp": "3GPP",
}


def _alias_key(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def is_valid_concept(name: str) -> bool:
    name = name.strip()
    if not name or len(name) < 2:
        return False
    if len(name) > MAX_CONCEPT_LEN:
        return False
    if NOISE_PREFIX_RE.match(name):
        return False
    if CODE_ARTIFACT_RE.search(name):
        return False
    if PAPER_TITLE_LIKE_RE.match(name) and len(name) > 60:
        return False
    if name.count(";") >= 2 or name.count(",") >= 4:
        return False
    return True


def normalize_concept_name(name: str) -> str | None:
    name = re.sub(r"\s+", " ", name.strip())
    if not is_valid_concept(name):
        return None
    canonical = CANONICAL_ALIASES.get(_alias_key(name))
    if canonical:
        return canonical
    # Strip trailing parenthetical if redundant short form exists
    bare = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
    if bare and bare != name:
        canonical = CANONICAL_ALIASES.get(_alias_key(bare))
        if canonical:
            return canonical
        if is_valid_concept(bare) and len(bare) >= 3:
            return bare
    return name


def clean_concepts(concepts: list[dict]) -> list[dict]:
    """Merge and filter concept dicts from LLM extraction."""
    merged: dict[str, dict] = {}
    for concept in concepts:
        raw_name = str(concept.get("name", "")).strip()
        name = normalize_concept_name(raw_name)
        if not name:
            continue
        key = _alias_key(name)
        existing = merged.get(
            key,
            {
                "name": name,
                "definition": "",
                "defines": False,
                "related_to": [],
                "sections": [],
            },
        )
        definition = str(concept.get("definition") or "").strip()
        if definition and not existing.get("definition"):
            existing["definition"] = definition
        if concept.get("defines"):
            existing["defines"] = True
        related = []
        for item in concept.get("related_to") or []:
            normalized = normalize_concept_name(str(item))
            if normalized and _alias_key(normalized) != key:
                related.append(normalized)
        existing["related_to"] = sorted(set(existing.get("related_to", []) + related))
        for section in concept.get("sections") or []:
            if section not in existing["sections"]:
                existing["sections"].append(section)
        merged[key] = existing
    return list(merged.values())
