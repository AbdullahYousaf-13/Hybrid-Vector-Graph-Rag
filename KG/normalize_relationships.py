import json
import re
from google import genai
from google.genai import types

STRUCTURAL_TYPES = {"HAS_SECTION", "HAS_CHUNK", "MENTIONED_IN"}

MAPPING_PROMPT = """You are cleaning up a knowledge graph's relationship types extracted from {domain_description}.

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


def build_canonical_mapping(api_key, rel_counts, model="gemini-3.5-flash-lite", domain_description="this text corpus"):
    client = genai.Client(api_key=api_key)
    rel_list = "\n".join(f'{r["relType"]}: {r["count"]}' for r in rel_counts)
    prompt = MAPPING_PROMPT.format(domain_description=domain_description, rel_list=rel_list)

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


def normalize_relationships(graph, api_key, domain_description="this text corpus"):
    rel_counts = get_relationship_counts(graph)
    print(f"Found {len(rel_counts)} non-structural relationship types to normalize.")
    mapping = build_canonical_mapping(api_key, rel_counts, domain_description=domain_description)
    apply_mapping(graph, mapping)
    return mapping


VERIFY_PROMPT = """You are verifying facts extracted from a knowledge graph against the actual source text
they came from. For each item below, you're given a claimed relationship "A [RELATION] B" and the real
passage it should have come from. Based ONLY on that passage (not any outside knowledge):
- If the relationship and direction are correct as stated, set "valid": true, "corrected_a": A, "corrected_b": B.
- If the passage supports the relationship but in the OPPOSITE direction, set "valid": true and SWAP
  corrected_a/corrected_b to the correct direction.
- If the passage does not actually support this relationship at all, set "valid": false.

Return ONLY a JSON array, one object per item, in the same order given:
[{{"index": 0, "valid": true, "corrected_a": "...", "corrected_b": "..."}}]

Items:
{items_block}
"""


def _find_grounding_chunk(graph, a_name, b_name):
    """A real chunk of source text both entities are mentioned in, if one exists."""
    rows = graph.query(
        """
        MATCH (a:Entity {name: $a})-[:MENTIONED_IN]->(c:Chunk)<-[:MENTIONED_IN]-(b:Entity {name: $b})
        RETURN c.text AS text
        LIMIT 1
        """,
        params={"a": a_name, "b": b_name},
    )
    return rows[0]["text"] if rows else None


def verify_relationships(graph, api_key, rel_types, batch_size=20, model="gemini-3.5-flash-lite"):
    """
    Grounded verification/correction pass for the given relationship type(s). For each edge,
    finds a real chunk both connected entities are mentioned in (via the MENTIONED_IN links
    already created during extraction) and asks the LLM to confirm, redirect, or drop the edge
    based on that actual source text — not on background knowledge. Works on any corpus, since
    it only relies on that corpus's own already-extracted text, never on the model "knowing" the
    subject matter.
    """
    client = genai.Client(api_key=api_key)
    type_pattern = "|".join(f"`{t}`" for t in rel_types)

    edges = graph.query(f"""
        MATCH (a:Entity)-[r:{type_pattern}]->(b:Entity)
        RETURN a.name AS a, type(r) AS relType, b.name AS b
    """)
    print(f"Verifying {len(edges)} edges of type(s): {', '.join(rel_types)}.")

    grounded = []
    for e in edges:
        text = _find_grounding_chunk(graph, e["a"], e["b"])
        if text:
            grounded.append({**e, "text": text})
    print(f"Found grounding text for {len(grounded)}/{len(edges)} edges "
          f"({len(edges) - len(grounded)} skipped — no shared source chunk to verify against).")

    fixed = removed = unchanged = 0
    for i in range(0, len(grounded), batch_size):
        batch = grounded[i:i + batch_size]
        items_block = "\n\n".join(
            f'[{j}] Claim: "{item["a"]}" {item["relType"]} "{item["b"]}"\nPassage: {item["text"][:1000]}'
            for j, item in enumerate(batch)
        )
        resp = client.models.generate_content(
            model=model,
            contents=VERIFY_PROMPT.format(items_block=items_block),
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
        )
        results = json.loads(resp.text)

        for result in results:
            item = batch[result["index"]]
            graph.query(
                f"""
                MATCH (a:Entity {{name: $a}})-[r:`{item['relType']}`]->(b:Entity {{name: $b}})
                DELETE r
                """,
                params={"a": item["a"], "b": item["b"]},
            )
            if not result.get("valid", False):
                removed += 1
                continue
            corrected_a, corrected_b = result["corrected_a"], result["corrected_b"]
            graph.query(
                f"""
                MATCH (a:Entity {{name: $a}}), (b:Entity {{name: $b}})
                MERGE (a)-[:`{item['relType']}`]->(b)
                """,
                params={"a": corrected_a, "b": corrected_b},
            )
            if corrected_a == item["a"]:
                unchanged += 1
            else:
                fixed += 1

    print(f"Verification done: {unchanged} confirmed correct, {fixed} direction-corrected, "
          f"{removed} removed (not supported by their source text).")


VERIFY_WITH_SOURCE_PROMPT = """You are verifying and cleaning up facts extracted from a knowledge graph
against the actual source passage each one came from. For each item, you're given a claimed relationship
"A [RELATION] B" and the exact passage it was extracted from. Based ONLY on that passage (not outside
knowledge):

- If A or B is a generic placeholder (a pronoun or bare kinship word like "mother", "his dad", "her sister",
  "the boy", "parents") rather than an actual proper name, and the passage reveals who it specifically refers
  to, replace it with that proper name. If the passage does not reveal a specific name for it, set
  "valid": false (too vague to keep).
- If the relationship and direction are correct as stated (after any name resolution above), set
  "valid": true, "corrected_a": A (or resolved name), "corrected_b": B (or resolved name).
- If the passage supports the relationship but in the OPPOSITE direction, set "valid": true and SWAP
  corrected_a/corrected_b (after resolving names) to the correct direction.
- If the passage does not actually support this relationship at all, set "valid": false.

Return ONLY a JSON array, one object per item, in the same order given:
[{{"index": 0, "valid": true, "corrected_a": "...", "corrected_b": "..."}}]

Items:
{items_block}
"""


def verify_relationships_with_source(graph, api_key, rel_types, batch_size=20, model="gemini-3.5-flash-lite"):
    """
    Like verify_relationships, but uses each edge's own recorded r.sourceChunk (set by
    extract_relationships_for_category) as grounding evidence instead of an arbitrary shared
    chunk. Edges with no sourceChunk (created before source tracking existed) are left
    completely untouched, since there's nothing real to verify them against. Also resolves or
    drops edges where an entity name is a generic placeholder (e.g. "mother") rather than a
    proper name, based on whether the source text reveals who it actually is. Deletes/rewrites
    only the exact edge matched by its own sourceChunk, never other edges between the same pair.
    """
    client = genai.Client(api_key=api_key)
    type_pattern = "|".join(f"`{t}`" for t in rel_types)

    edges = graph.query(f"""
        MATCH (a:Entity)-[r:{type_pattern}]->(b:Entity)
        WHERE r.sourceChunk IS NOT NULL
        RETURN a.name AS a, type(r) AS relType, b.name AS b, r.sourceChunk AS chunkId
    """)
    skipped_no_source = graph.query(f"""
        MATCH (a:Entity)-[r:{type_pattern}]->(b:Entity)
        WHERE r.sourceChunk IS NULL
        RETURN count(r) AS count
    """)[0]["count"]
    print(f"Verifying {len(edges)} edges with real source text "
          f"({skipped_no_source} left untouched — no sourceChunk to verify against).")

    fixed = removed = unchanged = 0
    for i in range(0, len(edges), batch_size):
        batch = edges[i:i + batch_size]
        chunk_ids = [item["chunkId"] for item in batch]
        chunk_rows = graph.query(
            "MATCH (c:Chunk) WHERE c.chunkId IN $ids RETURN c.chunkId AS chunkId, c.text AS text",
            params={"ids": chunk_ids},
        )
        text_by_id = {r["chunkId"]: r["text"] for r in chunk_rows}

        items_block = "\n\n".join(
            f'[{j}] Claim: "{item["a"]}" {item["relType"]} "{item["b"]}"\n'
            f'Passage: {text_by_id.get(item["chunkId"], "")[:1000]}'
            for j, item in enumerate(batch)
        )
        resp = client.models.generate_content(
            model=model,
            contents=VERIFY_WITH_SOURCE_PROMPT.format(items_block=items_block),
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
        )
        results = json.loads(resp.text)

        for result in results:
            item = batch[result["index"]]
            graph.query(
                f"""
                MATCH (a:Entity {{name: $a}})-[r:`{item['relType']}`]->(b:Entity {{name: $b}})
                WHERE r.sourceChunk = $chunkId
                DELETE r
                """,
                params={"a": item["a"], "b": item["b"], "chunkId": item["chunkId"]},
            )
            if not result.get("valid", False):
                removed += 1
                continue
            corrected_a, corrected_b = result["corrected_a"], result["corrected_b"]
            graph.query(
                f"""
                MERGE (a:Entity {{name: $a}})
                MERGE (b:Entity {{name: $b}})
                MERGE (a)-[r:`{item['relType']}`]->(b)
                  ON CREATE SET r.sourceChunk = $chunkId
                """,
                params={"a": corrected_a, "b": corrected_b, "chunkId": item["chunkId"]},
            )
            if corrected_a == item["a"] and corrected_b == item["b"]:
                unchanged += 1
            else:
                fixed += 1

    print(f"Verification done: {unchanged} confirmed correct, {fixed} corrected (direction and/or name), "
          f"{removed} removed (not supported, or too vague to resolve). {skipped_no_source} left untouched.")
