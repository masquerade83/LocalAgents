"""Prompt templates for Ollama graph extraction."""

PAPER_METADATA_PROMPT = """You extract structured metadata from a whitepaper.

Return ONLY valid JSON with this exact shape:
{{
  "title": "string",
  "authors": ["Author One", "Author Two"],
  "year": 2024,
  "abstract": "short abstract if present else empty string",
  "citations": [
    {{
      "title": "Referenced Paper Title",
      "authors": ["Lastname"],
      "year": 2018
    }}
  ]
}}

Rules:
- Use empty arrays/strings when unknown.
- Include only citations explicitly referenced in the text.
- Do not invent authors or papers.
- year must be an integer or null.

Paper title guess: {title}
Paper text:
{text}
"""


SECTION_CONCEPTS_PROMPT = """You extract concepts and relationships from a whitepaper section.

Return ONLY valid JSON with this exact shape:
{{
  "concepts": [
    {{
      "name": "Concept Name",
      "definition": "one sentence definition if stated, else empty string",
      "defines": true,
      "related_to": ["Other Concept"]
    }}
  ]
}}

Rules:
- Extract important technical concepts, methods, and domain terms.
- Set defines=true only when the section explicitly defines the concept.
- related_to should list concept names mentioned as related in this section.
- Do not invent concepts not supported by the section.
- Keep concept names concise and consistent (Title Case).

Paper: {paper_title}
Section: {section_title}
Section text:
{text}
"""
