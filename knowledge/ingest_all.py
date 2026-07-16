#!/usr/bin/env python3
"""Orchestrate Neo4j graph ingest and Chroma vector embed."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from config import WHITEPAPERS_MODULE_DIR, WHITEPAPERS_PATH
from embed_chroma import embed_corpus, reset_collection

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_graph_ingest(
    corpus_path: Path,
    *,
    paper: str | None = None,
    model: str = "qwen2.5:7b",
    reset: bool = False,
) -> None:
    cmd = [
        sys.executable,
        str(WHITEPAPERS_MODULE_DIR / "ingest.py"),
        "--path",
        str(corpus_path),
        "--model",
        model,
    ]
    if paper:
        cmd.extend(["--paper", paper])
    if reset:
        cmd.append("--reset")
    logger.info("Running graph ingest: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=WHITEPAPERS_PATH)
    parser.add_argument("--paper", help="Process a single PDF")
    parser.add_argument("--graph-only", action="store_true")
    parser.add_argument("--vectors-only", action="store_true")
    parser.add_argument("--reset-graph", action="store_true")
    parser.add_argument("--reset-vectors", action="store_true")
    parser.add_argument("--model", default="qwen2.5:7b")
    args = parser.parse_args(argv)

    corpus = args.path.expanduser().resolve()

    if not args.vectors_only:
        run_graph_ingest(
            corpus,
            paper=args.paper,
            model=args.model,
            reset=args.reset_graph,
        )
        if not args.graph_only:
            # Clean noisy concepts after graph ingest
            cleanup_cmd = [sys.executable, str(WHITEPAPERS_MODULE_DIR / "cleanup_graph.py")]
            subprocess.run(cleanup_cmd, check=True)

    if not args.graph_only:
        if args.reset_vectors:
            reset_collection()
        stats = embed_corpus(corpus, single_paper=args.paper)
        logger.info("Vector embed complete — papers: %s, chunks: %s", stats["papers"], stats["chunks"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
