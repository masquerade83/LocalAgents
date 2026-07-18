#!/usr/bin/env python3
"""Ingest local PDF whitepapers into a Neo4j knowledge graph."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from config import CACHE_DIR, OLLAMA_MODEL, RAG_CHUNK_CHARS, WHITEPAPERS_PATH
from extract_graph import enrich_paper_with_graph
from extract_pdf import extract_pdf
from load_neo4j import Neo4jLoader

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def discover_pdfs(root: Path, single_paper: str | None = None) -> list[Path]:
    if single_paper:
        path = Path(single_paper)
        if not path.is_absolute():
            path = (root / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Paper not found: {path}")
        return [path]

    return sorted(root.rglob("*.pdf"))


def cache_path_for(pdf_path: Path) -> Path:
    return CACHE_DIR / f"{pdf_path.stem}.json"


def load_or_extract_pdf(pdf_path: Path, chunk_chars: int) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = cache_path_for(pdf_path)
    if cache_file.exists():
        logger.info("Using cached PDF extraction: %s", cache_file.name)
        return json.loads(cache_file.read_text(encoding="utf-8"))

    payload = extract_pdf(pdf_path, chunk_chars=chunk_chars)
    cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def ingest_paper(
    pdf_path: Path,
    loader: Neo4jLoader,
    *,
    skip_llm: bool,
    model: str,
    max_sections: int | None,
    chunk_chars: int,
    refresh_cache: bool,
) -> None:
    if refresh_cache:
        cache_file = cache_path_for(pdf_path)
        if cache_file.exists():
            cache_file.unlink()

    paper = load_or_extract_pdf(pdf_path, chunk_chars=chunk_chars)
    if not skip_llm:
        logger.info("Running LLM extraction for %s", pdf_path.name)
        paper = enrich_paper_with_graph(paper, model=model, max_sections=max_sections)
        enriched_cache = CACHE_DIR / f"{pdf_path.stem}.enriched.json"
        enriched_cache.write_text(json.dumps(paper, indent=2), encoding="utf-8")
    else:
        paper.setdefault("concepts", [])
        paper.setdefault("citations", [])

    loader.load_paper(paper)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=WHITEPAPERS_PATH,
        help="Folder containing PDF whitepapers",
    )
    parser.add_argument(
        "--paper",
        help="Ingest a single PDF file (relative to --path unless absolute)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing whitepaper subgraph before ingest",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Apply Neo4j schema constraints/indexes and exit",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Load PDF structure only (no Ollama extraction)",
    )
    parser.add_argument(
        "--model",
        default=OLLAMA_MODEL,
        help="Ollama model for extraction",
    )
    parser.add_argument(
        "--max-sections",
        type=int,
        default=None,
        help="Limit section chunks sent to LLM (useful for testing)",
    )
    parser.add_argument(
        "--chunk-chars",
        type=int,
        default=RAG_CHUNK_CHARS,
        help="Maximum characters per section chunk",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Re-extract PDF text even if cache exists",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    corpus_path = args.path.expanduser().resolve()
    corpus_path.mkdir(parents=True, exist_ok=True)

    with Neo4jLoader() as loader:
        loader.apply_schema()
        if args.schema_only:
            logger.info("Schema applied.")
            return 0

        if args.reset:
            loader.reset_whitepapers()

        pdfs = discover_pdfs(corpus_path, single_paper=args.paper)
        if not pdfs:
            logger.warning("No PDFs found in %s", corpus_path)
            logger.warning("Add PDFs to the corpus folder and re-run ingest.")
            return 1

        for pdf_path in pdfs:
            logger.info("Ingesting %s", pdf_path)
            ingest_paper(
                pdf_path,
                loader,
                skip_llm=args.skip_llm,
                model=args.model,
                max_sections=args.max_sections,
                chunk_chars=args.chunk_chars,
                refresh_cache=args.refresh_cache,
            )

        stats = loader.stats()
        logger.info(
            "Graph stats — papers: %(papers)s, authors: %(authors)s, concepts: %(concepts)s, citations: %(citations)s",
            stats,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
