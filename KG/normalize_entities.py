import json
from google import genai
from google.genai import types

ENTITY_MAPPING_PROMPT = """You are cleaning up entity names in a knowledge graph built from {domain_description}.

Below is a list of entities: their name, type, how many relationships they're involved in, and a short excerpt
of REAL TEXT where each one is actually mentioned (their evidence). Some of these are alias variants of the
SAME real entity, referred to differently in different places (e.g. a short form, a nickname, a fuller/formal
name, an abbreviation).

Using ONLY the evidence text given for each entity (not outside/background knowledge), group CLEAR alias
variants of the same specific entity together, and pick the fullest/most proper name as the canonical one.
Do NOT merge entities that are merely similar-looking or related but are actually distinct according to their
evidence — if the evidence doesn't make it clear they're the same, leave them separate.
If an entity has no clear alias in this list, map it to itself.

Return ONLY a JSON object mapping every input name to its canonical name, like:
{{"John": "John Smith", "John Smith": "John Smith", "Acme": "Acme Corporation", ...}}

Every name from the input list must appear exactly once as a key.

Input entities (name | type | relationship count | evidence):
{entity_list}
"""


def get_entity_evidence(graph, limit=400, evidence_chunks_per_entity=2, evidence_chars=300):
    """
    Top-N most-connected entities, each paired with a short excerpt of real text
    from up to `evidence_chunks_per_entity` chunks it's actually mentioned in
    (via existing MENTIONED_IN links) — grounding for alias-merging decisions
    instead of relying on the LLM's own background knowledge of the name.
    """
    entities = graph.query("""
        MATCH (e:Entity)
        OPTIONAL MATCH (e)-[r]-()
        RETURN e.name AS name, e.type AS type, count(r) AS count
        ORDER BY count DESC
        LIMIT $limit
    """, params={"limit": limit})

    result = []
    for e in entities:
        chunks = graph.query("""
            MATCH (ent:Entity {name: $name})-[:MENTIONED_IN]->(c:Chunk)
            RETURN c.text AS text
            LIMIT $n
        """, params={"name": e["name"], "n": evidence_chunks_per_entity})
        evidence = " [...] ".join(c["text"][:evidence_chars] for c in chunks) if chunks else "(no evidence found)"
        result.append({**e, "evidence": evidence})
    return result


def build_entity_mapping(api_key, entities_with_evidence, model="gemini-3.5-flash-lite",
                          domain_description="this text corpus"):
    client = genai.Client(api_key=api_key)
    entity_list = "\n".join(
        f'{e["name"]} | {e["type"]} | {e["count"]} | {e["evidence"]}' for e in entities_with_evidence
    )
    prompt = ENTITY_MAPPING_PROMPT.format(domain_description=domain_description, entity_list=entity_list)

    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0,
        ),
    )
    return json.loads(resp.text)


def merge_entity(graph, old_name, canonical_name):
    """Redirects every relationship (any type, any direction) from old_name onto
    canonical_name, then deletes the now-orphaned old node. No APOC required."""
    graph.query("MERGE (c:Entity {name: $name})", params={"name": canonical_name})

    out_rels = graph.query(
        "MATCH (old:Entity {name: $old})-[r]->() RETURN DISTINCT type(r) AS relType",
        params={"old": old_name},
    )
    for row in out_rels:
        rel_type = row["relType"]
        graph.query(
            f"""
            MATCH (old:Entity {{name: $old}})-[r:`{rel_type}`]->(other)
            MATCH (canon:Entity {{name: $canonical}})
            MERGE (canon)-[:`{rel_type}`]->(other)
            DELETE r
            """,
            params={"old": old_name, "canonical": canonical_name},
        )

    in_rels = graph.query(
        "MATCH ()-[r]->(old:Entity {name: $old}) RETURN DISTINCT type(r) AS relType",
        params={"old": old_name},
    )
    for row in in_rels:
        rel_type = row["relType"]
        graph.query(
            f"""
            MATCH (other)-[r:`{rel_type}`]->(old:Entity {{name: $old}})
            MATCH (canon:Entity {{name: $canonical}})
            MERGE (other)-[:`{rel_type}`]->(canon)
            DELETE r
            """,
            params={"old": old_name, "canonical": canonical_name},
        )

    graph.query("MATCH (old:Entity {name: $old}) DETACH DELETE old", params={"old": old_name})


def normalize_entities(graph, api_key, limit=400, domain_description="this text corpus"):
    entities = get_entity_evidence(graph, limit=limit)
    print(f"Checking top {len(entities)} entities for alias duplicates (grounded in their own mention text).")
    mapping = build_entity_mapping(api_key, entities, domain_description=domain_description)

    merged = 0
    for old_name, canonical_name in mapping.items():
        if old_name != canonical_name:
            merge_entity(graph, old_name, canonical_name)
            merged += 1
    print(f"Merged {merged} alias entities into their canonical form.")
    return mapping
