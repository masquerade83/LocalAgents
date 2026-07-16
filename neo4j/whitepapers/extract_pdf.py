"""Extract text and sections from PDF whitepapers."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import fitz

SECTION_HEADING_RE = re.compile(
    r"^(?:\d+(?:\.\d+)*[\.\)]?\s+)?([A-Z][A-Za-z0-9 \-/&]{2,60})$"
)
NUMBERED_HEADING_RE = re.compile(
    r"^(?:\d+(?:\.\d+)+\s+|\d+\.\s+)([A-Z][A-Za-z0-9 \-/&]{2,60})$"
)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def slugify(text: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not slug:
        slug = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return slug[:max_len]


def paper_id_from_path(path: Path) -> str:
    return slugify(path.stem)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pages(path: Path) -> list[str]:
    doc = fitz.open(path)
    pages: list[str] = []
    try:
        for page in doc:
            pages.append(normalize_whitespace(page.get_text("text")))
    finally:
        doc.close()
    return pages


def guess_title(pages: list[str], fallback: str) -> str:
    if not pages:
        return fallback
    first_page_lines = [line.strip() for line in pages[0].splitlines() if line.strip()]
    candidates = [line for line in first_page_lines[:8] if 8 <= len(line) <= 180]
    if candidates:
        return candidates[0]
    return fallback


def guess_year(full_text: str) -> int | None:
    years = [int(match.group(0)) for match in YEAR_RE.finditer(full_text[:4000])]
    if not years:
        return None
    return max(years)


def guess_abstract(full_text: str) -> str:
    match = re.search(
        r"(?is)\babstract\b[:\s]*(.{80,2000}?)(?:\n\s*\n|\bintroduction\b|\b1[\.\)]?\s+introduction\b)",
        full_text,
    )
    if match:
        return normalize_whitespace(match.group(1))[:2000]
    return ""


def split_into_sections(full_text: str) -> list[dict[str, Any]]:
    lines = full_text.splitlines()
    sections: list[dict[str, Any]] = []
    current_title = "Body"
    current_lines: list[str] = []
    order = 0

    def flush() -> None:
        nonlocal order
        text = normalize_whitespace("\n".join(current_lines))
        if not text:
            return
        sections.append({"title": current_title, "order": order, "text": text})
        order += 1

    for line in lines:
        stripped = line.strip()
        if not stripped:
            current_lines.append("")
            continue

        heading_match = NUMBERED_HEADING_RE.match(stripped) or SECTION_HEADING_RE.match(stripped)
        if heading_match and len(stripped) < 80:
            flush()
            current_title = heading_match.group(1).strip()
            current_lines = []
            continue

        current_lines.append(stripped)

    flush()

    if not sections:
        sections.append({"title": "Body", "order": 0, "text": full_text[:120000]})

    return sections


def chunk_section_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        paragraph_len = len(paragraph) + 2
        if current and current_len + paragraph_len > max_chars:
            chunks.append("\n\n".join(current))
            current = [paragraph]
            current_len = paragraph_len
        else:
            current.append(paragraph)
            current_len += paragraph_len

    if current:
        chunks.append("\n\n".join(current))

    return chunks or [text[:max_chars]]


def extract_pdf(path: Path, chunk_chars: int = 6000) -> dict[str, Any]:
    path = path.resolve()
    pages = extract_pages(path)
    full_text = normalize_whitespace("\n\n".join(pages))
    title = guess_title(pages, fallback=path.stem.replace("_", " "))
    paper_id = paper_id_from_path(path)
    sections = split_into_sections(full_text)

    section_payload: list[dict[str, Any]] = []
    for section in sections:
        for chunk_index, chunk_text in enumerate(chunk_section_text(section["text"], chunk_chars)):
            section_payload.append(
                {
                    "title": section["title"],
                    "order": section["order"],
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                }
            )

    return {
        "paper_id": paper_id,
        "title": title,
        "year": guess_year(full_text),
        "abstract": guess_abstract(full_text),
        "authors": [],
        "sections": section_payload,
        "source_path": str(path),
        "full_text_preview": full_text[:8000],
    }
