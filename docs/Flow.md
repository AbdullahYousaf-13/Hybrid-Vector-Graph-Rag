# Flow

Data and control flow for both phases. Diagrams are Mermaid — GitHub renders
them inline.

---

## 1. Ingestion flow (`prep.ipynb`)

```mermaid
flowchart TD
    A[data/*.json<br/>section_name to section_text] --> B[split_data_from_file<br/>RecursiveCharacterTextSplitter<br/>2000 / 200]
    B --> C[chunk dicts<br/>chunkId, text, source, chunkSeqId]

    A --> D[create_nodes]
    D --> D1[MERGE Person or Event<br/>name = filename id]
    D --> D2[MERGE Section per JSON key<br/>type, parent_name]

    C --> E[ingest_Chunks<br/>MERGE Chunk on chunkId]

    D1 --> F[create_relationship x5]
    D2 --> F
    E --> F
    F --> F1[Section-HAS_CHUNK-Chunk]
    F --> F2[Person-RELATED_TO-Person]
    F --> F3[Person-RELATED_TO-Event]
    F --> F4[Person-HAS_SECTION-Section]
    F --> F5[Event-HAS_SECTION-Section]

    F --> G[create_vector_index<br/>Chunk / textEmbedding / 768 / cosine]
    G --> H[embed_text]
    H --> H1[MATCH Chunk WHERE textEmbedding IS NULL]
    H1 --> H2[Gemini gemini-embedding-001<br/>RETRIEVAL_DOCUMENT, 768d]
    H2 --> H3[L2 normalize]
    H3 --> H4[db.create.setNodeVectorProperty]
    H4 -. batch 32 + backoff on 429 .- H1

    H4 --> Z[(Neo4j Aura<br/>db 3663f87a)]
    D1 --> Z
    D2 --> Z
    E --> Z
    F1 --> Z
```

Idempotent: nodes `MERGE` on keys; `embed_text` skips chunks that already have
`textEmbedding`.

---

## 2. Vector RAG query flow (`query_vector_rag`)

```mermaid
sequenceDiagram
    participant U as Caller (main.ipynb)
    participant V as vectorRAG.py
    participant G as Gemini
    participant N as Neo4j (Chunk index)

    U->>V: query_vector_rag(question, "Chunk", "Chunk", "text", "textEmbedding")
    V->>G: embed question (RETRIEVAL_QUERY, 768d)
    G-->>V: query vector
    V->>N: db.index.vector.queryNodes(Chunk, k=4, vector)
    N-->>V: top-4 chunk texts
    V->>V: join texts into <context>
    V->>G: prompt(context, question) via gemini-3.6-flash
    G-->>V: answer text
    V->>V: StrOutputParser + textwrap.fill(60)
    V-->>U: answer
```

Prompt rule: answer **only** from `<context>`; otherwise "I don't know".

---

## 3. Graph RAG query flow (`generate_cypher_query`)

```mermaid
sequenceDiagram
    participant U as Caller (main.ipynb)
    participant R as GraphRAG.py
    participant N as Neo4j
    participant G as Gemini (gemini-3.6-flash)

    U->>R: generate_cypher_query(question, graph)
    R->>N: MATCH Person/Event RETURN names
    N-->>R: entity name catalog
    R->>R: build PromptTemplate(schema, question, entity_names)
    R->>G: "write a Cypher query"
    G-->>R: Cypher (names constrained to the catalog)
    R->>N: run Cypher
    N-->>R: rows
    R->>G: "summarize these rows for the question"
    G-->>R: answer text
    R->>R: textwrap.fill(60)
    R-->>U: answer
```

`allow_dangerous_requests=True` is required because the LLM-authored Cypher runs
directly against the database.

---

## 4. How the two paths differ

| | Vector RAG | Graph RAG |
|---|---|---|
| Retrieves | chunk **text** by semantic similarity | **rows** via generated Cypher |
| Knows about | anything written in the prose (e.g. Wellington, Blücher) | only modelled nodes (Talleyrand, Napoleon, Battle_of_Waterloo) |
| Best question | "What reforms did Napoleon introduce?" | "How many Person nodes are there?" / "Who is related to Battle_of_Waterloo?" |
| Failure mode | misses facts not in the top-k chunks | empty result if Cypher name/shape is wrong |

The intended hybrid step: run both, feed vector chunks **and** Cypher rows into
one final Gemini prompt.
