import json
import re
import time
from tqdm import tqdm
from google import genai
from google.genai import types

ENTITY_EXTRACTION_PROMPT = """You are extracting a knowledge graph from Harry Potter book text.

For each chunk below, identify:
- entities: named characters, places, spells, magical objects, creatures, or organizations mentioned (skip generic/common nouns)
- relationships: meaningful connections between two entities found in THIS chunk (e.g. FRIEND_OF, TEACHES, ATTENDS, LOCATED_IN, CASTS, MEMBER_OF, ENEMY_OF)

Return ONLY a JSON array, one object per chunk, in the same order as given, with this exact shape:
[
  {{
    "chunkId": "<chunk id>",
    "entities": [{{"name": "...", "type": "Character|Location|Spell|Object|Creature|Organization"}}],
    "relationships": [{{"source": "...", "relation": "UPPER_SNAKE_CASE", "target": "..."}}]
  }}
]

If a chunk has no clear entities/relationships, return empty lists for it. Do not invent facts not in the text.

Chunks:
{chunks_block}
"""


def _sanitize_rel_type(relation: str) -> str:
    """Keep only A-Z, 0-9, underscore; guarantees safe interpolation into Cypher."""
    cleaned = re.sub(r'[^A-Za-z0-9_]', '_', relation.upper()).strip('_')
    return cleaned or "RELATED_TO"


def _call_gemini_json(client, model, prompt, max_attempts=6):
    for attempt in range(max_attempts):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0,
                ),
            )
            return json.loads(resp.text)
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            match = re.search(r"'retryDelay':\s*'(\d+)s'", str(e))
            wait = int(match.group(1)) + 5 if match else 2 ** (attempt + 3)
            print(f"  retry in {wait}s ({e})")
            time.sleep(wait)


def extract_entities(graph, api_key, batch_size=15, book_filter=None, model="gemini-3.5-flash-lite"):
    """
    Reads Chunk text from Neo4j, asks Gemini to extract entities + relationships
    per chunk, and MERGEs the results into the graph as :Entity nodes linked to
    their source Chunk via :MENTIONED_IN, with typed relationships between entities.
    """
    client = genai.Client(api_key=api_key)

    filter_clause = "WHERE c.node_name = $book" if book_filter else ""
    chunks = list(graph.query(f"""
        MATCH (c:Chunk) {filter_clause}
        RETURN c.chunkId AS chunkId, c.text AS text
    """, params={"book": book_filter} if book_filter else {}))
    print(f"Extracting entities from {len(chunks)} chunks.")

    for i in tqdm(range(0, len(chunks), batch_size), desc="Extracting", ncols=100):
        batch = chunks[i:i + batch_size]
        chunks_block = "\n\n".join(
            f'[{c["chunkId"]}]\n{c["text"]}' for c in batch
        )
        prompt = ENTITY_EXTRACTION_PROMPT.format(chunks_block=chunks_block)

        results = _call_gemini_json(client, model, prompt)

        for item in results:
            chunk_id = item.get("chunkId")
            if not chunk_id:
                continue

            for ent in item.get("entities", []):
                name = (ent.get("name") or "").strip()
                etype = (ent.get("type") or "Unknown").strip()
                if not name:
                    continue
                graph.query(
                    """
                    MERGE (e:Entity {name: $name})
                      ON CREATE SET e.type = $type
                    WITH e
                    MATCH (c:Chunk {chunkId: $chunkId})
                    MERGE (e)-[:MENTIONED_IN]->(c)
                    """,
                    params={"name": name, "type": etype, "chunkId": chunk_id},
                )

            for rel in item.get("relationships", []):
                source = (rel.get("source") or "").strip()
                target = (rel.get("target") or "").strip()
                relation = _sanitize_rel_type(rel.get("relation") or "")
                if not source or not target:
                    continue
                graph.query(
                    f"""
                    MERGE (a:Entity {{name: $source}})
                    MERGE (b:Entity {{name: $target}})
                    MERGE (a)-[:{relation}]->(b)
                    """,
                    params={"source": source, "target": target},
                )

        time.sleep(4)  # stay comfortably under free-tier RPM (15/min for this model)

    print("Finished entity extraction.")
