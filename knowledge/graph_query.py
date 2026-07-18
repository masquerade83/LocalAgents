"""Neo4j graph query helpers for GraphRAG."""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, GRAPH_CONCEPT_LIMIT


class GraphQuery:
    def __init__(self) -> None:
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self) -> None:
        self.driver.close()

    def __enter__(self) -> "GraphQuery":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def stats(self) -> dict[str, int]:
        queries = {
            "papers": "MATCH (p:Paper) WHERE NOT coalesce(p.is_stub,false) RETURN count(p) AS c",
            "concepts": "MATCH (c:Concept) RETURN count(c) AS c",
            "citations": "MATCH ()-[r:CITES]->() RETURN count(r) AS c",
            "chunks": "RETURN 0 AS c",
        }
        out: dict[str, int] = {}
        with self.driver.session() as session:
            for key, q in queries.items():
                if key == "chunks":
                    continue
                rec = session.run(q).single()
                out[key] = int(rec["c"]) if rec else 0
        return out

    def list_papers(self) -> list[dict[str, Any]]:
        with self.driver.session() as session:
            return [
                dict(r)
                for r in session.run(
                    """
                    MATCH (p:Paper)
                    WHERE NOT coalesce(p.is_stub, false)
                    RETURN p.id AS id, p.title AS title, p.year AS year
                    ORDER BY p.title
                    """
                )
            ]

    def search_concepts(self, keyword: str, limit: int = GRAPH_CONCEPT_LIMIT) -> list[str]:
        with self.driver.session() as session:
            return [
                r["name"]
                for r in session.run(
                    """
                    MATCH (c:Concept)
                    WHERE toLower(c.name) CONTAINS toLower($keyword)
                    RETURN c.name AS name
                    ORDER BY size(c.name)
                    LIMIT $limit
                    """,
                    keyword=keyword,
                    limit=limit,
                )
            ]

    def papers_for_concept(self, concept: str) -> list[dict[str, Any]]:
        with self.driver.session() as session:
            return [
                dict(r)
                for r in session.run(
                    """
                    MATCH (p:Paper)-[:MENTIONS]->(c:Concept)
                    WHERE toLower(c.name) CONTAINS toLower($concept)
                      AND NOT coalesce(p.is_stub, false)
                    RETURN DISTINCT p.id AS paper_id, p.title AS title
                    ORDER BY title
                    """,
                    concept=concept,
                )
            ]

    def paper_ids_for_keywords(self, keywords: list[str]) -> list[str]:
        if not keywords:
            return []
        with self.driver.session() as session:
            return [
                r["paper_id"]
                for r in session.run(
                    """
                    UNWIND $keywords AS kw
                    MATCH (p:Paper)-[:MENTIONS]->(c:Concept)
                    WHERE toLower(c.name) CONTAINS toLower(kw)
                      AND NOT coalesce(p.is_stub, false)
                    RETURN DISTINCT p.id AS paper_id
                    """,
                    keywords=keywords,
                )
            ]

    def graph_context_for_papers(self, paper_ids: list[str]) -> str:
        if not paper_ids:
            return ""
        with self.driver.session() as session:
            rows = session.run(
                """
                UNWIND $paper_ids AS pid
                MATCH (p:Paper {id: pid})
                OPTIONAL MATCH (p)-[:MENTIONS]->(c:Concept)
                WITH p, collect(DISTINCT c.name)[..8] AS concepts
                RETURN p.title AS title, concepts
                """,
                paper_ids=paper_ids,
            )
            lines = []
            for row in rows:
                concepts = ", ".join(row["concepts"][:8]) if row["concepts"] else "none"
                lines.append(f"- {row['title']}: concepts [{concepts}]")
            return "\n".join(lines)

    def concept_bridge(self, limit: int = 15) -> list[dict[str, Any]]:
        with self.driver.session() as session:
            return [
                dict(r)
                for r in session.run(
                    """
                    MATCH (p1:Paper)-[:MENTIONS]->(c:Concept)<-[:MENTIONS]-(p2:Paper)
                    WHERE p1 <> p2
                      AND NOT coalesce(p1.is_stub,false)
                      AND NOT coalesce(p2.is_stub,false)
                    RETURN c.name AS concept, p1.title AS paper1, p2.title AS paper2
                    LIMIT $limit
                    """,
                    limit=limit,
                )
            ]
