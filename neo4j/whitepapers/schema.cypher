// Whitepaper knowledge graph schema — run once via ingest.py --schema-only

CREATE CONSTRAINT paper_id IF NOT EXISTS
FOR (p:Paper) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT author_name IF NOT EXISTS
FOR (a:Author) REQUIRE a.name IS UNIQUE;

CREATE CONSTRAINT concept_name IF NOT EXISTS
FOR (c:Concept) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT section_id IF NOT EXISTS
FOR (s:Section) REQUIRE s.id IS UNIQUE;

CREATE INDEX paper_title IF NOT EXISTS
FOR (p:Paper) ON (p.title);

CREATE INDEX paper_year IF NOT EXISTS
FOR (p:Paper) ON (p.year);
