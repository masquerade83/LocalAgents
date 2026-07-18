#!/usr/bin/env python3
"""Clean noisy and orphan concepts in the Neo4j whitepaper graph."""

from __future__ import annotations

import argparse
import logging
import sys

from concept_cleanup import normalize_concept_name
from load_neo4j import Neo4jLoader

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _merge_concept(session, old_name: str, new_name: str, definition: str) -> None:
    session.run(
        """
        MERGE (target:Concept {name: $new_name})
        SET target.definition = CASE
            WHEN $definition <> '' THEN $definition
            ELSE coalesce(target.definition, '')
        END
        WITH target
        MATCH (source:Concept {name: $old_name})
        OPTIONAL MATCH (p:Paper)-[:MENTIONS]->(source)
        FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
            MERGE (p)-[:MENTIONS]->(target)
        )
        WITH source, target
        OPTIONAL MATCH (p:Paper)-[:DEFINES]->(source)
        FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
            MERGE (p)-[:DEFINES]->(target)
        )
        WITH source, target
        OPTIONAL MATCH (source)-[:RELATED_TO]->(other:Concept)
        FOREACH (_ IN CASE WHEN other IS NOT NULL THEN [1] ELSE [] END |
            MERGE (target)-[:RELATED_TO]->(other)
        )
        WITH source, target
        OPTIONAL MATCH (other:Concept)-[:RELATED_TO]->(source)
        FOREACH (_ IN CASE WHEN other IS NOT NULL THEN [1] ELSE [] END |
            MERGE (other)-[:RELATED_TO]->(target)
        )
        WITH source, target
        OPTIONAL MATCH (source)-[:APPEARS_IN]->(s:Section)
        FOREACH (_ IN CASE WHEN s IS NOT NULL THEN [1] ELSE [] END |
            MERGE (target)-[:APPEARS_IN]->(s)
        )
        WITH source
        DETACH DELETE source
        """,
        old_name=old_name,
        new_name=new_name,
        definition=definition,
    )


def cleanup_graph(loader: Neo4jLoader, *, dry_run: bool = False) -> dict[str, int]:
    stats = {
        "total_before": 0,
        "deleted_invalid": 0,
        "merged_aliases": 0,
        "orphans_removed": 0,
        "total_after": 0,
    }

    with loader.driver.session() as session:
        rows = list(session.run("MATCH (c:Concept) RETURN c.name AS name, c.definition AS definition"))
        stats["total_before"] = len(rows)

        for row in rows:
            name = row["name"]
            normalized = normalize_concept_name(name)
            if normalized is None:
                stats["deleted_invalid"] += 1
                if not dry_run:
                    session.run("MATCH (c:Concept {name: $name}) DETACH DELETE c", name=name)
            elif normalized != name:
                stats["merged_aliases"] += 1
                if not dry_run:
                    _merge_concept(session, name, normalized, row.get("definition") or "")

        if not dry_run:
            result = session.run(
                """
                MATCH (c:Concept)
                WHERE NOT (()-[:MENTIONS|DEFINES|RELATED_TO|APPEARS_IN]->(c))
                  AND NOT (c)-[:RELATED_TO|APPEARS_IN]->()
                WITH c DETACH DELETE c
                RETURN count(*) AS removed
                """
            ).single()
            stats["orphans_removed"] = int(result["removed"]) if result else 0

        after = session.run("MATCH (c:Concept) RETURN count(c) AS c").single()
        stats["total_after"] = int(after["c"]) if after else stats["total_before"]

    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report only, no changes")
    args = parser.parse_args(argv)

    with Neo4jLoader() as loader:
        before = loader.stats()
        stats = cleanup_graph(loader, dry_run=args.dry_run)
        after = loader.stats()

    logger.info(
        "Cleanup — concepts %s → %s (invalid: %s, merged: %s, orphans: %s)",
        stats["total_before"],
        stats["total_after"],
        stats["deleted_invalid"],
        stats["merged_aliases"],
        stats["orphans_removed"],
    )
    logger.info(
        "Graph stats — papers: %(papers)s, authors: %(authors)s, concepts: %(concepts)s, citations: %(citations)s",
        after if not args.dry_run else before,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
