import json
import re
from google import genai
from google.genai import types

STRUCTURAL_TYPES = {"HAS_SECTION", "HAS_CHUNK", "MENTIONED_IN"}

MAPPING_PROMPT = """You are cleaning up a knowledge graph's relationship types extracted from Harry Potter book text.

Below is a list of relationship type names currently used in the graph, with how many times each appears.
Many of these mean the same thing but were named inconsistently (e.g. OWNS, OWNER_OF, OWNED_BY, POSSESSES all mean ownership).

Group them into a small set of canonical, UPPER_SNAKE_CASE relationship types (aim for roughly 30-50 canonical types total)
that best represent the distinct real-world relationship categories present. Merge near-synonyms and directional
variants into ONE canonical name each — if two types are the same relationship in opposite directions
(e.g. OWNS vs OWNED_BY), pick ONE canonical direction, don't create both.

Return ONLY a JSON object mapping every input type name to its canonical type name, like:
{{"OWNS": "OWNS", "OWNER_OF": "OWNS", "OWNED_BY": "OWNS", "POSSESSES": "OWNS", ...}}

Every key from the input list must appear exactly once in the output.

Input relationship types (name: count):
{rel_list}
"""


def _sanitize_rel_type(name: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9_]', '_', name.upper()).strip('_')
    return cleaned or "RELATED_TO"


def get_relationship_counts(graph, exclude=STRUCTURAL_TYPES):
    rows = graph.query("MATCH ()-[r]->() RETURN type(r) AS relType, count(*) AS count ORDER BY count DESC")
    return [row for row in rows if row["relType"] not in exclude]


def build_canonical_mapping(api_key, rel_counts, model="gemini-3.5-flash-lite"):
    client = genai.Client(api_key=api_key)
    rel_list = "\n".join(f'{r["relType"]}: {r["count"]}' for r in rel_counts)
    prompt = MAPPING_PROMPT.format(rel_list=rel_list)

    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0,
        ),
    )
    raw_mapping = json.loads(resp.text)

    mapping = {}
    for old_type, canonical in raw_mapping.items():
        mapping[old_type] = _sanitize_rel_type(canonical)
    return mapping


def apply_mapping(graph, mapping):
    """Rewrites every non-structural relationship to its canonical type."""
    changed = 0
    for old_type, canonical in mapping.items():
        if old_type == canonical:
            continue
        graph.query(
            f"""
            MATCH (a)-[r:`{old_type}`]->(b)
            MERGE (a)-[:`{canonical}`]->(b)
            DELETE r
            """
        )
        changed += 1
    print(f"Rewrote {changed} relationship types to their canonical form.")


def normalize_relationships(graph, api_key):
    rel_counts = get_relationship_counts(graph)
    print(f"Found {len(rel_counts)} non-structural relationship types to normalize.")
    mapping = build_canonical_mapping(api_key, rel_counts)
    apply_mapping(graph, mapping)
    return mapping
