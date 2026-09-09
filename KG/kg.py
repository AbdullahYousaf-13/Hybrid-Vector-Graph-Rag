from tqdm import tqdm


# 1. Add main nodes without creating relationships
def create_nodes(graph, data: dict, node_label: str, node_name: str):
    # Create the main node
    main_node_query = f"""
    MERGE (main:{node_label} {{name: $name}})
    """
    graph.query(main_node_query, params={"name": node_name})

    # Create section nodes only (without relationships)
    for section, content in data.items():
        query = f"""
        MERGE (s:Section {{type: $type, parent_name: $name}})
     
        """
        params = {
            "type": section,
            "name": node_name
        }
        graph.query(query, params=params)


# 2. Add Chunks
def ingest_Chunks(graph, chunks, node_name, node_label):
    """
    Ingests file chunk data into the knowledge graph by merging chunk nodes.

    Args:
        graph: A knowledge graph client or connection object that has a `query` method.
        chunks: A list of dictionaries, each representing a file chunk with keys:
                     'chunkId', 'text', 'source', 'formItem', and 'chunkSeqId'.
        node_name: A string used to tag the chunk nodes.
        node_label: The dynamic label for the chunk nodes.
    """
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


# 3. Create Relationships

def create_relationship(graph, query: str):
    """
    Executes the provided Cypher query on the given graph.
    
    Parameters:
        graph: An instance of your Neo4j connection.
        query: A string containing a valid Cypher query.
    """
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




def embed_text(graph, api_key, node_name, batch_size=100):
    """Embed all nodes of `node_name` that lack an embedding, using Gemini."""
    import time
    import numpy as np
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    MODEL = "gemini-embedding-001"
    DIMS = 768

    print("Starting embedding update...")
    nodes = list(graph.query(f"""
        MATCH (n:{node_name})
        WHERE n.textEmbedding IS NULL
        RETURN elementId(n) AS node_id, n.text AS text
    """))
    print(f"Found {len(nodes)} nodes without embeddings.")

    for i in tqdm(range(0, len(nodes), batch_size), desc="Embedding", ncols=100):
        batch = nodes[i:i + batch_size]
        texts = [r["text"] or "" for r in batch]

        # retry on rate-limit / transient errors
        for attempt in range(5):
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
                if attempt == 4:
                    raise
                wait = 2 ** attempt
                print(f"  retry in {wait}s ({e})")
                time.sleep(wait)

        for rec, emb in zip(batch, resp.embeddings):
            # gemini-embedding-001 needs manual normalization for non-3072 dims
            v = np.array(emb.values, dtype=float)
            v = (v / np.linalg.norm(v)).tolist()
            graph.query(
                f"""
                MATCH (n:{node_name}) WHERE elementId(n) = $node_id
                CALL db.create.setNodeVectorProperty(n, 'textEmbedding', $vector)
                """,
                params={"node_id": rec["node_id"], "vector": v},
            )
        time.sleep(1)  # stay under free-tier RPM

    print("Finished embedding update.")