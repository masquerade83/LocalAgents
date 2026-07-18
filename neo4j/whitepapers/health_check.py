#!/usr/bin/env python3
"""Run quick health check on the whitepaper knowledge graph."""

from __future__ import annotations

import sys

from load_neo4j import Neo4jLoader


def run_health_check() -> dict:
    results: dict = {}
    with Neo4jLoader() as loader:
        with loader.driver.session() as session:
            results["stats"] = loader.stats()
            results["ingested_papers"] = session.run(
                """
                MATCH (p:Paper) WHERE NOT coalesce(p.is_stub, false)
                RETURN count(p) AS c
                """
            ).single()["c"]
            results["stub_papers"] = session.run(
                "MATCH (p:Paper {is_stub: true}) RETURN count(p) AS c"
            ).single()["c"]
            results["concepts_per_paper"] = [
                dict(r)
                for r in session.run(
                    """
                    MATCH (p:Paper)-[:MENTIONS]->(c:Concept)
                    WHERE NOT coalesce(p.is_stub, false)
                    RETURN p.title AS paper, count(DISTINCT c) AS concepts
                    ORDER BY concepts
                    """
                )
            ]
            results["low_concept_papers"] = [
                dict(r)
                for r in session.run(
                    """
                    MATCH (p:Paper)
                    WHERE NOT coalesce(p.is_stub, false)
                    OPTIONAL MATCH (p)-[:MENTIONS]->(c:Concept)
                    WITH p, count(c) AS n WHERE n < 10
                    RETURN p.title AS paper, n AS concepts
                    """
                )
            ]
            results["orphan_concepts"] = session.run(
                """
                MATCH (c:Concept)
                WHERE NOT (()-[:MENTIONS|DEFINES|RELATED_TO|APPEARS_IN]->(c))
                  AND NOT (c)-[:RELATED_TO|APPEARS_IN]->()
                RETURN count(c) AS c
                """
            ).single()["c"]
            results["noisy_concepts"] = [
                r["name"]
                for r in session.run(
                    """
                    MATCH (c:Concept) WHERE size(c.name) > 60
                    RETURN c.name AS name ORDER BY size(c.name) DESC LIMIT 10
                    """
                )
            ]
            results["gold_questions"] = {
                "o_ran_papers": [
                    r["paper"]
                    for r in session.run(
                        """
                        MATCH (p:Paper)-[:MENTIONS]->(c:Concept)
                        WHERE NOT coalesce(p.is_stub, false)
                          AND (toLower(c.name) CONTAINS 'o-ran' OR toLower(c.name) = 'openran')
                        RETURN DISTINCT p.title AS paper
                        """
                    )
                ],
                "telcogpt": session.run(
                    """
                    MATCH (p:Paper {id: 'telcogpt'})
                    RETURN p.title AS title, p.year AS year
                    """
                ).single(),
                "survey_paper": session.run(
                    """
                    MATCH (p:Paper)
                    WHERE toLower(p.title) CONTAINS 'comprehensive survey'
                    RETURN p.title AS title LIMIT 1
                    """
                ).single(),
                "llm_bridge_count": session.run(
                    """
                    MATCH (p1:Paper)-[:MENTIONS]->(c:Concept)<-[:MENTIONS]-(p2:Paper)
                    WHERE p1 <> p2 AND NOT coalesce(p1.is_stub,false) AND NOT coalesce(p2.is_stub,false)
                      AND toLower(c.name) CONTAINS 'llm'
                    RETURN count(*) AS c
                    """
                ).single()["c"],
                "gpu_paper": session.run(
                    """
                    MATCH (p:Paper)
                    WHERE toLower(p.title) CONTAINS 'gpu accelerated'
                    RETURN p.title AS title LIMIT 1
                    """
                ).single(),
            }
    return results


def main() -> int:
    r = run_health_check()
    stats = r["stats"]
    print("=== Quick Health Check ===")
    print(f"Papers: {stats['papers']} (ingested: {r['ingested_papers']}, stubs: {r['stub_papers']})")
    print(f"Authors: {stats['authors']} | Concepts: {stats['concepts']} | Citations: {stats['citations']}")
    print(f"Orphan concepts: {r['orphan_concepts']}")
    print(f"Noisy concepts (>60 chars): {len(r['noisy_concepts'])}")
    print("\nConcepts per paper:")
    for row in r["concepts_per_paper"]:
        flag = " ⚠️" if row["concepts"] < 10 else ""
        print(f"  {row['concepts']:4d}  {row['paper']}{flag}")
    if r["low_concept_papers"]:
        print("\nLow concept papers:", r["low_concept_papers"])
    if r["noisy_concepts"]:
        print("\nTop noisy concepts:")
        for name in r["noisy_concepts"][:5]:
            print(f"  - {name[:90]}...")
    g = r["gold_questions"]
    print("\nGold questions:")
    print(f"  O-RAN papers: {len(g['o_ran_papers'])} — {g['o_ran_papers']}")
    print(f"  TelcoGPT: {g['telcogpt']}")
    print(f"  Survey: {g['survey_paper']}")
    print(f"  LLM bridges: {g['llm_bridge_count']}")
    print(f"  GPU paper: {g['gpu_paper']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
