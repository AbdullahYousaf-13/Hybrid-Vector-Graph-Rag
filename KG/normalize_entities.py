import json
from google import genai
from google.genai import types

ENTITY_MAPPING_PROMPT = """You are cleaning up character/place/entity names in a Harry Potter knowledge graph.

Below is a list of entity names, their type, and how many relationships they're involved in.
Some of these are just alias variants of the SAME real entity (e.g. "Harry" and "Harry Potter" are the same
character; "Hogwarts" and "Hogwarts School of Witchcraft and Wizardry" are the same place).

Group only CLEAR alias variants of the same specific entity together, and pick the fullest/most proper
name as the canonical one (e.g. "Harry Potter" over "Harry"). Do NOT merge entities that are merely similar
or related but are actually distinct (e.g. "Hogwarts" and "Hogwarts Express" are DIFFERENT things, don't merge).
If an entity has no clear alias in this list, map it to itself.

Return ONLY a JSON object mapping every input name to its canonical name, like:
{{"Harry": "Harry Potter", "Harry Potter": "Harry Potter", "Hogwarts": "Hogwarts", ...}}

Every name from the input list must appear exactly once as a key.

Input entities (name | type | relationship count):
{entity_list}
"""


def get_entity_counts(graph, limit=400):
    rows = graph.query("""
        MATCH (e:Entity)
        OPTIONAL MATCH (e)-[r]-()
        RETURN e.name AS name, e.type AS type, count(r) AS count
        ORDER BY count DESC
        LIMIT $limit
    """, params={"limit": limit})
    return rows


def build_entity_mapping(api_key, entity_counts, model="gemini-3.5-flash-lite"):
    client = genai.Client(api_key=api_key)
    entity_list = "\n".join(f'{e["name"]} | {e["type"]} | {e["count"]}' for e in entity_counts)
    prompt = ENTITY_MAPPING_PROMPT.format(entity_list=entity_list)

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


def normalize_entities(graph, api_key, limit=400):
    entity_counts = get_entity_counts(graph, limit=limit)
    print(f"Checking top {len(entity_counts)} entities for alias duplicates.")
    mapping = build_entity_mapping(api_key, entity_counts)

    merged = 0
    for old_name, canonical_name in mapping.items():
        if old_name != canonical_name:
            merge_entity(graph, old_name, canonical_name)
            merged += 1
    print(f"Merged {merged} alias entities into their canonical form.")
    return mapping
