from tqdm import tqdm


def create_nodes(graph, data: dict, node_label: str, node_name: str):
    main_node_query = f"""
    MERGE (main:{node_label} {{name: $name}})
    """
    graph.query(main_node_query, params={"name": node_name})

    for section, content in data.items():
        query = f"""
        MERGE (s:Section {{type: $type, parent_name: $name}})
     
        """
        params = {
            "type": section,
            "name": node_name
        }
        graph.query(query, params=params)


def ingest_Chunks(graph, chunks, node_name, node_label):
    merge_chunk_node_query = f"""
    MERGE (mergedChunk:{node_label} {{chunkId: $chunkParam.chunkId}})
        ON CREATE SET
            mergedChunk.text = $chunkParam.text, 
            mergedChunk.source = $chunkParam.Source, 
            mergedChunk.formItem = $chunkParam.formItem, 
            mergedChunk.chunkSeqId = $chunkParam.chunkSeqId,
            mergedChunk.node_name = $node_name
    RETURN mergedChunk
    """

    node_count = 0
    for chunk in chunks:
        print(f"Creating `:{node_label}` node for chunk ID {chunk['chunkId']}")
        graph.query(merge_chunk_node_query, params={'chunkParam': chunk, 'node_name': node_name})
        node_count += 1
    print(f"Created {node_count} nodes")


def create_relationship(graph, query: str):
    graph.query(query)


def create_vector_index(graph, index_name):
    vector_index_query = f"""
    CREATE VECTOR INDEX `{index_name}` IF NOT EXISTS
    FOR (n:{index_name}) ON (n.textEmbedding)
    OPTIONS {{ indexConfig: {{
        `vector.dimensions`: 768,
        `vector.similarity_function`: 'cosine'
    }}}}
    """
    graph.query(vector_index_query)


def embed_text(graph, api_key, node_name, batch_size=100, book_filter=None):
    import time
    import re
    import numpy as np
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    MODEL = "gemini-embedding-001"
    DIMS = 768

    print("Starting embedding update...")
    filter_clause = "AND n.node_name = $book" if book_filter else ""
    nodes = list(graph.query(f"""
        MATCH (n:{node_name})
        WHERE n.textEmbedding IS NULL {filter_clause}
        RETURN elementId(n) AS node_id, n.text AS text
    """, params={"book": book_filter} if book_filter else {}))
    print(f"Found {len(nodes)} nodes without embeddings.")

    for i in tqdm(range(0, len(nodes), batch_size), desc="Embedding", ncols=100):
        batch = nodes[i:i + batch_size]
        texts = [r["text"] or "" for r in batch]

        for attempt in range(6):
            try:
                resp = client.models.embed_content(
                    model=MODEL,
                    contents=texts,
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT",
                        output_dimensionality=DIMS,
                    ),
                )
                break
            except Exception as e:
                if attempt == 5:
                    raise
                match = re.search(r"'retryDelay':\s*'(\d+)s'", str(e))
                wait = int(match.group(1)) + 5 if match else 2 ** (attempt + 3)
                print(f"  retry in {wait}s ({e})")
                time.sleep(wait)

        for rec, emb in zip(batch, resp.embeddings):
            v = np.array(emb.values, dtype=float)
            v = (v / np.linalg.norm(v)).tolist()
            graph.query(
                f"""
                MATCH (n:{node_name}) WHERE elementId(n) = $node_id
                CALL db.create.setNodeVectorProperty(n, 'textEmbedding', $vector)
                """,
                params={"node_id": rec["node_id"], "vector": v},
            )
        time.sleep(2)

    print("Finished embedding update.")