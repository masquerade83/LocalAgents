#!/usr/bin/env python3
"""Manual spot-check: compare Neo4j graph facts against PDF text for one paper."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from extract_pdf import extract_pdf
from load_neo4j import Neo4jLoader

DEFAULT_PAPER = "TelcoGPT.pdf"


def _in_text(needle: str, haystack: str) -> bool:
    return needle.lower() in haystack.lower()


def spot_check(pdf_path: Path, paper_id: str | None = None) -> dict:
    extracted = extract_pdf(pdf_path)
    paper_id = paper_id or extracted["paper_id"]
    full_text = "\n\n".join(
        section.get("text", "") for section in extracted.get("sections", [])
    )
    if not full_text:
        full_text = extracted.get("full_text_preview", "")

    with Neo4jLoader() as loader:
        with loader.driver.session() as session:
            paper = session.run(
                """
                MATCH (p:Paper {id: $paper_id})
                RETURN p.title AS title, p.year AS year
                """,
                paper_id=paper_id,
            ).single()
            authors = [
                r["name"]
                for r in session.run(
                    """
                    MATCH (a:Author)-[:AUTHORED]->(p:Paper {id: $paper_id})
                    RETURN a.name AS name ORDER BY name
                    """,
                    paper_id=paper_id,
                )
            ]
            concepts = [
                r["name"]
                for r in session.run(
                    """
                    MATCH (p:Paper {id: $paper_id})-[:MENTIONS]->(c:Concept)
                    RETURN c.name AS name ORDER BY name
                    """,
                    paper_id=paper_id,
                )
            ]
            citations = [
                r["title"]
                for r in session.run(
                    """
                    MATCH (p:Paper {id: $paper_id})-[:CITES]->(c:Paper)
                    RETURN c.title AS title ORDER BY title
                    """,
                    paper_id=paper_id,
                )
            ]

    author_checks = [
        {"name": name, "in_pdf": _in_text(name.split()[-1], full_text) or _in_text(name, full_text)}
        for name in authors
    ]

    concept_sample = concepts[:20]
    concept_checks = [{"name": name, "in_pdf": _in_text(name.split("(")[0].strip(), full_text)} for name in concept_sample]

    citation_checks = [{"title": title, "in_pdf": _in_text(title.split("(")[0].strip()[:30], full_text)} for title in citations]

    title_ok = bool(paper) and _in_text(extracted["title"][:40], full_text)

    return {
        "paper_id": paper_id,
        "pdf": str(pdf_path),
        "title_in_pdf": title_ok,
        "graph_title": paper["title"] if paper else None,
        "graph_year": paper["year"] if paper else None,
        "authors": author_checks,
        "authors_found_in_pdf": sum(1 for a in author_checks if a["in_pdf"]),
        "authors_total": len(author_checks),
        "concept_sample": concept_checks,
        "concepts_in_pdf_sample": sum(1 for c in concept_checks if c["in_pdf"]),
        "concept_sample_size": len(concept_checks),
        "concepts_total_in_graph": len(concepts),
        "citations": citation_checks,
        "citations_in_pdf": sum(1 for c in citation_checks if c["in_pdf"]),
        "citations_total": len(citation_checks),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", default=DEFAULT_PAPER)
    parser.add_argument("--path", type=Path, default=Path(__file__).resolve().parents[2] / "whitepapers")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    pdf_path = args.path / args.paper
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    report = spot_check(pdf_path)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"Spot check: {report['graph_title']} ({report['paper_id']})")
    print(f"Title in PDF: {'OK' if report['title_in_pdf'] else 'MISS'}")
    print(f"Authors in PDF: {report['authors_found_in_pdf']}/{report['authors_total']}")
    for author in report["authors"]:
        mark = "OK" if author["in_pdf"] else "??"
        print(f"  [{mark}] {author['name']}")
    print(f"Concept sample in PDF: {report['concepts_in_pdf_sample']}/{report['concept_sample_size']} (graph total: {report['concepts_total_in_graph']})")
    for concept in report["concept_sample"][:10]:
        mark = "OK" if concept["in_pdf"] else "??"
        print(f"  [{mark}] {concept['name']}")
    print(f"Citations in PDF: {report['citations_in_pdf']}/{report['citations_total']}")
    for citation in report["citations"]:
        mark = "OK" if citation["in_pdf"] else "??"
        print(f"  [{mark}] {citation['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
