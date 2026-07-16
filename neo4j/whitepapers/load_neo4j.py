"""Load extracted whitepaper graph data into Neo4j."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

from config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, SCHEMA_PATH
from extract_pdf import slugify

logger = logging.getLogger(__name__)

WHITEPAPER_LABELS = ("Paper", "Author", "Concept", "Section", "Claim")


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def paper_id_from_title(title: str) -> str:
    return slugify(title)


class Neo4jLoader:
    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def __enter__(self) -> "Neo4jLoader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def run(self, query: str, **params: Any) -> None:
        with self.driver.session() as session:
            session.run(query, **params)

    def apply_schema(self, schema_path: Path = SCHEMA_PATH) -> None:
        statements = [
            statement.strip()
            for statement in schema_path.read_text(encoding="utf-8").split(";")
            if statement.strip() and not statement.strip().startswith("//")
        ]
        with self.driver.session() as session:
            for statement in statements:
                session.run(statement)
        logger.info("Applied schema from %s", schema_path)

    def reset_whitepapers(self) -> None:
        query = """
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN $labels)
        DETACH DELETE n
        """
        with self.driver.session() as session:
            session.run(query, labels=list(WHITEPAPER_LABELS))
        logger.info("Cleared whitepaper subgraph")

    def load_paper(self, paper: dict[str, Any]) -> None:
        paper_id = paper["paper_id"]
        title = paper.get("title") or paper_id
        year = paper.get("year")
        abstract = paper.get("abstract") or ""
        source_path = paper.get("source_path") or ""

        with self.driver.session() as session:
            session.run(
                """
                MERGE (p:Paper {id: $paper_id})
                SET p.title = $title,
                    p.year = $year,
                    p.abstract = $abstract,
                    p.source_path = $source_path,
                    p.normalized_title = $normalized_title,
                    p.is_stub = false
                """,
                paper_id=paper_id,
                title=title,
                year=year,
                abstract=abstract,
                source_path=source_path,
                normalized_title=normalize_title(title),
            )

            for author_name in paper.get("authors") or []:
                author_name = str(author_name).strip()
                if not author_name:
                    continue
                session.run(
                    """
                    MERGE (a:Author {name: $name})
                    WITH a
                    MATCH (p:Paper {id: $paper_id})
                    MERGE (a)-[:AUTHORED]->(p)
                    """,
                    name=author_name,
                    paper_id=paper_id,
                )

            seen_sections: set[str] = set()
            for section in paper.get("sections") or []:
                order = int(section.get("order", 0))
                section_title = section.get("title") or f"Section {order}"
                section_id = f"{paper_id}::section::{order}"
                if section_id in seen_sections:
                    continue
                seen_sections.add(section_id)
                session.run(
                    """
                    MERGE (s:Section {id: $section_id})
                    SET s.title = $title,
                        s.order = $order
                    WITH s
                    MATCH (p:Paper {id: $paper_id})
                    MERGE (s)-[:PART_OF]->(p)
                    """,
                    section_id=section_id,
                    title=section_title,
                    order=order,
                    paper_id=paper_id,
                )

            for concept in paper.get("concepts") or []:
                name = str(concept.get("name", "")).strip()
                if not name:
                    continue
                definition = str(concept.get("definition") or "").strip()
                session.run(
                    """
                    MERGE (c:Concept {name: $name})
                    SET c.definition = CASE
                        WHEN $definition <> '' THEN $definition
                        ELSE coalesce(c.definition, '')
                    END
                    WITH c
                    MATCH (p:Paper {id: $paper_id})
                    MERGE (p)-[m:MENTIONS]->(c)
                    SET m.source = 'llm'
                    """,
                    name=name,
                    definition=definition,
                    paper_id=paper_id,
                )

                if concept.get("defines"):
                    session.run(
                        """
                        MATCH (p:Paper {id: $paper_id})
                        MATCH (c:Concept {name: $name})
                        MERGE (p)-[:DEFINES]->(c)
                        """,
                        paper_id=paper_id,
                        name=name,
                    )

                for related_name in concept.get("related_to") or []:
                    related_name = str(related_name).strip()
                    if not related_name or related_name.lower() == name.lower():
                        continue
                    session.run(
                        """
                        MERGE (c1:Concept {name: $name})
                        MERGE (c2:Concept {name: $related_name})
                        MERGE (c1)-[:RELATED_TO]->(c2)
                        """,
                        name=name,
                        related_name=related_name,
                    )

                for section_key in concept.get("sections") or []:
                    try:
                        order = int(str(section_key).split("::")[0])
                    except (ValueError, IndexError):
                        continue
                    section_id = f"{paper_id}::section::{order}"
                    session.run(
                        """
                        MATCH (c:Concept {name: $name})
                        MATCH (s:Section {id: $section_id})
                        MERGE (c)-[:APPEARS_IN]->(s)
                        """,
                        name=name,
                        section_id=section_id,
                    )

            for citation in paper.get("citations") or []:
                cited_title = str(citation.get("title") or "").strip()
                if not cited_title:
                    continue
                cited_id = paper_id_from_title(cited_title)
                cited_year = citation.get("year")
                cited_authors = citation.get("authors") or []
                session.run(
                    """
                    MERGE (target:Paper {id: $cited_id})
                    ON CREATE SET target.title = $cited_title,
                                  target.year = $cited_year,
                                  target.normalized_title = $normalized_title,
                                  target.is_stub = true
                    ON MATCH SET target.title = coalesce(target.title, $cited_title),
                                 target.year = coalesce(target.year, $cited_year),
                                 target.normalized_title = coalesce(target.normalized_title, $normalized_title)
                    WITH target
                    MATCH (source:Paper {id: $paper_id})
                    MERGE (source)-[:CITES]->(target)
                    """,
                    cited_id=cited_id,
                    cited_title=cited_title,
                    cited_year=cited_year,
                    normalized_title=normalize_title(cited_title),
                    paper_id=paper_id,
                )
                for author_name in cited_authors:
                    author_name = str(author_name).strip()
                    if not author_name:
                        continue
                    session.run(
                        """
                        MERGE (a:Author {name: $name})
                        WITH a
                        MATCH (p:Paper {id: $cited_id})
                        MERGE (a)-[:AUTHORED]->(p)
                        """,
                        name=author_name,
                        cited_id=cited_id,
                    )

        logger.info("Loaded paper %s (%s)", paper_id, title)

    def stats(self) -> dict[str, int]:
        queries = {
            "papers": "MATCH (p:Paper) RETURN count(p) AS c",
            "authors": "MATCH (a:Author) RETURN count(a) AS c",
            "concepts": "MATCH (c:Concept) RETURN count(c) AS c",
            "citations": "MATCH ()-[r:CITES]->() RETURN count(r) AS c",
        }
        results: dict[str, int] = {}
        with self.driver.session() as session:
            for key, query in queries.items():
                record = session.run(query).single()
                results[key] = int(record["c"]) if record else 0
        return results
