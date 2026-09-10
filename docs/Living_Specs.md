# Living Specification — Hybrid Vector + Graph RAG

> A "living" spec: it describes the system **as it is today**, not a frozen plan.
> Update it whenever behaviour, schema, or the stack changes.

Last updated: 2026-09-10

---

## 1. Purpose

Answer natural-language questions about a small history corpus (Napoleon,
Talleyrand, the Battle of Waterloo) two complementary ways:

| Path | Good at | Backed by |
|------|---------|-----------|
| **Vector RAG** | open-ended questions, facts stated in prose | embeddings over chunk text |
| **Graph RAG** | precise structured questions (counts, relationships, "who is linked to X") | generated Cypher over the graph |

The end goal is a *hybrid* answer that uses both retrievers together. Today the
two paths are callable but invoked separately (see §7).

---

## 2. Stack

| Concern | Choice | Notes |
|---|---|---|
| Graph DB | **Neo4j Aura Free** (instance `HVGR`, id `3663f87a`) | DB name **and** username are both `3663f87a`, not `neo4j` — set via `NEO4J_DATABASE` |
| Embeddings | **Gemini `gemini-embedding-001`**, 768 dims | computed in Python, L2-normalized; free tier |
| Chat / Cypher LLM | **Gemini `gemini-3.6-flash`** | free tier; ignores `temperature`; returns `content` as a list → needs `StrOutputParser` |
| Orchestration | **LangChain v1.4** + `langchain-neo4j` + `langchain-google-genai` | `langchain.chains` no longer exists; chains built with LCEL (`prompt \| llm \| parser`) |
| Chunking | `RecursiveCharacterTextSplitter` | `chunk_size=2000`, `chunk_overlap=200` |

Original upstream project used OpenAI throughout. It was migrated to Gemini
because the OpenAI account had no credits. No OpenAI dependency remains.

---

## 3. Repository layout

```
KG/
  config.py      load_neo4j_graph() -> (graph, GEMINI_API_KEY, None)
  chunking.py    split_data_from_file(path) -> list[chunk dict]
  kg.py          create_nodes, ingest_Chunks, create_relationship,
                 create_vector_index, embed_text
vectorRAG.py     query_vector_rag(question, index, label, text_prop, emb_prop)
GraphRAG.py      generate_cypher_query(question, graph)
prep.ipynb       one-time ingestion pipeline (§5)
main.ipynb       query entry point (§6)
data/*.json      source corpus: {section_name: section_text}
docs/            this spec + Flow.md
```

---

## 4. Data model (current graph)

### Nodes

| Label | Count | Key properties |
|---|---|---|
| `Chunk` | 150 | `chunkId` (unique), `text`, `source` (= JSON section), `chunkSeqId`, `node_name`, `textEmbedding` (768-float) |
| `Section` | 13 | `type` (= JSON section name), `parent_name` |
| `Person` | 2 | `name` — `Talleyrand`, `Napoleon` |
| `Event` | 1 | `name` — `Battle_of_Waterloo` |

`name` values are **filename-derived ids** (underscores, no spaces), not
Wikipedia titles. `GraphRAG.py` injects the real list into the Cypher prompt so
the LLM stops inventing slugs.

### Relationships

| Pattern | Rule |
|---|---|
| `(Section)-[:HAS_CHUNK]->(Chunk)` | `s.type = c.source AND s.parent_name = c.node_name` |
| `(Person)-[:RELATED_TO]->(Person)` | every pair, **both directions** |
| `(Person)-[:RELATED_TO]->(Event)` | every pair, **both directions** |
| `(Person)-[:HAS_SECTION]->(Section)` | `p.name = s.parent_name` |
| `(Event)-[:HAS_SECTION]->(Section)` | `e.name = s.parent_name` |

### Vector index

`CREATE VECTOR INDEX Chunk FOR (n:Chunk) ON (n.textEmbedding)` — 768 dims, cosine.

---

## 5. Ingestion pipeline (`prep.ipynb`)

1. `load_neo4j_graph()` — connect to Aura.
2. For each file in `["Talleyrand", "Napoleon", "Battle_of_Waterloo"]`:
   - `split_data_from_file` — load JSON, split each section into ≤2000-char chunks.
   - `create_nodes` — MERGE the `Person`/`Event` node + one `Section` per JSON key.
   - `ingest_Chunks` — MERGE a `Chunk` per chunk (idempotent on `chunkId`).
3. `create_relationship` × 5 — build the edges in §4.
4. `create_vector_index` — create the 768-dim `Chunk` index.
5. `embed_text` — for every `Chunk` with `textEmbedding IS NULL`:
   - embed text with Gemini (`RETRIEVAL_DOCUMENT`, 768 dims), L2-normalize,
   - write back with `db.create.setNodeVectorProperty`,
   - batched (32) with exponential backoff honouring the API's `retryDelay`
     (free tier = 100 embed requests/min; each item in a batch counts as 1).

Re-running is safe: nodes MERGE on keys, embeddings skip already-filled nodes.

---

## 6. Query paths

### `query_vector_rag` (`vectorRAG.py`)

```
question
  -> Neo4jVector.from_existing_graph (Gemini query-embedding, 768d)
  -> retriever.invoke(question)         # top k=4 chunks by cosine
  -> stuff chunk text into <context>
  -> ChatPromptTemplate | gemini-3.6-flash | StrOutputParser
  -> answer (wrapped to 60 cols)
```

Answers strictly from retrieved chunk text ("say you don't know" otherwise).

### `generate_cypher_query` (`GraphRAG.py`)

```
question
  -> _entity_name_catalog(graph)        # real Person/Event names
  -> PromptTemplate(schema, question, entity_names)
  -> GraphCypherQAChain.from_llm(gemini-3.6-flash, allow_dangerous_requests=True)
       -> LLM writes Cypher -> run on graph -> LLM summarizes rows
  -> answer (wrapped to 60 cols)
```

---

## 7. Known limitations / tech debt

| # | Issue | Impact |
|---|---|---|
| 1 | `RELATED_TO` created in both directions | undirected matches return each node twice |
| 2 | `Person↔Person` / `Person↔Event` edges are blanket (all pairs), not derived from content | "related to" is not meaningful yet |
| 3 | `main.ipynb` calls the two retrievers separately | not a true hybrid answer |
| 4 | Imports use `from VectorRAG import …` but file is `vectorRAG.py` | works on Windows, breaks on Linux/CI |
| 5 | No `requirements.txt` / lockfile | environment not reproducible |
| 6 | `id()` used in relationship Cypher (`prep.ipynb`) | deprecation warnings; use `elementId()` |
| 7 | Secrets (Gemini key, Neo4j password) appeared in a chat transcript | rotate when convenient |
| 8 | `main.ipynb` outputs committed with a stress-test question | tidy before sharing |

---

## 8. Roadmap

- [ ] Merge vector + graph context into a single hybrid prompt in `main.ipynb`.
- [ ] Derive `RELATED_TO` from co-occurrence in chunk text instead of all-pairs.
- [ ] Single-direction relationships + `elementId()`.
- [ ] `requirements.txt` (langchain, langchain-neo4j, langchain-google-genai, langchain-text-splitters, neo4j, python-dotenv, tqdm, numpy).
- [ ] Rename `vectorRAG.py` → `VectorRAG.py` (or fix the imports) for portability.
- [ ] Add a couple of evaluation questions with expected answers.
