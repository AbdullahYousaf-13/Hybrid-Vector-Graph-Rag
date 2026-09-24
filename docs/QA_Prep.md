# RAG Exact Call Chain

Format: **Trigger → calls → calls → ...** Each arrow is one function calling the next.
*Italic line under each step = what that step does.*

---

## A. Ingestion pipeline (triggered by running `prep.ipynb` cells in order)

**Cell 1 — connect**
`load_neo4j_graph()` (`KG/config.py`) → returns `graph`, `gemini_api`
*Opens the Neo4j connection and loads the Gemini key everything else in the notebook reuses.*

**Cell 2 — per-book ingest loop** (loops over the 7 book files)
`split_data_from_file(file)` (`KG/chunking.py`)
*Loads one book's JSON and splits each chapter's text into overlapping chunks.*
→ `text_splitter.split_text(item_text)` (LangChain splitter)
*Does the actual character-based splitting (chunk_size=2000, overlap=200).*
→ returns `chunks` list
*A list of chunk dicts (text + chunkId + metadata), one book at a time.*

then, still inside the same loop iteration:
`create_nodes(graph, data, "Book", name)` (`KG/kg.py`) → `graph.query(...)` MERGEs the `Book` node + `Section` nodes
*Creates the book node and one Section node per chapter, no relationships yet.*
→ `ingest_Chunks(graph, chunks, name, "Chunk")` (`KG/kg.py`) → `graph.query(...)` MERGEs one `Chunk` node per chunk
*Writes every chunk from step above as its own Chunk node.*

**Cell 3 — link the tree**
`create_relationship(graph, rel_section_chunk_query)` (`KG/kg.py`) → `graph.query(...)` → `Section-[:HAS_CHUNK]->Chunk`
*Connects each Section to the Chunks that belong to it.*
→ `create_relationship(graph, rel_book_section_query)` → `graph.query(...)` → `Book-[:HAS_SECTION]->Section`
*Connects each Book to its Sections, completing the Book→Section→Chunk tree.*

**Cell 4 — vector index**
`create_vector_index(graph, "Chunk")` (`KG/kg.py`) → `graph.query(...)` → `CREATE VECTOR INDEX`
*Creates the Neo4j vector index (768-dim, cosine) on Chunk.textEmbedding that vector search will use later.*

**Cell 5 — entity extraction loop** (loops over the 7 books)
`extract_entities(graph, api_key, book_filter=name)` (`KG/entities.py`)
*Reads that book's chunks and asks Gemini to pull out entities and relationships from each.*
→ `graph.query(...)` fetches that book's `Chunk` text
*Gets the raw chunk text to send to the LLM.*
→ `_call_gemini_json(client, model, ENTITY_EXTRACTION_PROMPT)` → Gemini call → `results`
*Sends a batch of chunks to Gemini and parses back structured JSON (entities + relationships per chunk).*
→ per result: `graph.query(...)` MERGEs `Entity` nodes + `MENTIONED_IN` edges + typed relationship edges
*Writes each extracted entity/relationship into the graph.*

**Cell 6 — embedding loop** (loops over the 7 books)
`embed_text(graph, api_key, "Chunk", book_filter=name)` (`KG/kg.py`)
*Embeds every Chunk in that book that doesn't have a vector yet.*
→ `graph.query(...)` fetches `Chunk` nodes missing `textEmbedding`
*Finds which chunks still need an embedding (so reruns don't redo work).*
→ `client.models.embed_content(...)` (Gemini) → embeddings
*Calls Gemini's embedding model on a batch of chunk texts.*
→ normalize vector → `graph.query(...)` → `db.create.setNodeVectorProperty(...)` per node
*L2-normalizes each vector and writes it onto its Chunk node.*

---

## B. Query-time (triggered per incoming question, by calling one of these three functions directly)

### Vector mode
`query_vector_rag(question, ...)` (`rag/vector_rag.py`)
*Answers by embedding the question and retrieving similar chunks.*
→ `_validate_and_sanitize_question(question)`
*Rejects empty/too-long questions and strips stray newlines/tabs.*
→ `daily_limiter.check_and_increment()`
*Counts this against the shared daily LLM-call quota.*
→ `get_vector_store(...)` → `vector_store`
*Returns the cached connection to the Chunk vector index (built once at server startup via `Neo4jVector.from_existing_graph`, not on every question).*
→ `vector_store.as_retriever(k=6).invoke(question)` → `docs`
*Embeds the question and returns the 6 most similar chunks.*
→ build `context` from `docs`
*Joins those chunks into one context string, truncated to 8000 chars.*
→ `chain = prompt | llm | StrOutputParser()` → `chain.invoke(...)` → `result`
*Asks the LLM to answer the question using only that context.*
→ return `{"answer": ..., "chunks": ...}`
*Returns the answer plus the raw chunks used, for transparency.*

### Graph mode
`generate_cypher_query(question, graph)` (`rag/graph_rag.py`)
*Answers by having the LLM write and run a Cypher query against the graph.*
→ `_validate_and_sanitize_question(question)`
*Same input guardrail as vector mode.*
→ `daily_limiter.check_and_increment()`
*Same quota check.*
→ `_entity_name_catalog(graph)` → `graph.query(...)` → `entity_names`
*Pulls a real, direct-from-the-database list of every valid entity name, to stop the LLM guessing names.*
→ `GraphCypherQAChain.from_llm(...)` → `cypher_chain`
*Builds LangChain's "generate Cypher → run it → answer from rows" chain.*
→ patches `graph.query` to `_guarded_query` (→ `_enforce_readonly_cypher` → `_ensure_cypher_limit` → real `graph.query`)
*Wraps the one method that actually executes Cypher so every query gets checked before it runs.*
→ `cypher_chain.invoke({"query": question})` → internally: LLM generates Cypher → `_guarded_query(cypher)` runs it → LLM turns rows into an answer → `response`
*The LLM writes Cypher for the question, the guarded query runs it safely, then a second LLM call turns the returned rows (at most 5) into a sentence. If the Cypher is invalid (`CypherSyntaxError`), it retries once, then raises a `ValueError` the user sees as a clear 400.*
→ restores real `graph.query`
*Un-patches the method so later calls aren't affected.*
→ return `{"answer": ..., "cypher_query": ...}`
*Returns the answer plus the exact Cypher that ran, for transparency.*

### Hybrid mode
`query_hybrid_rag(question, graph, ...)` (`rag/hybrid_rag.py`)
*Answers by running both modes above and reconciling their answers.*
→ `_validate_and_sanitize_question(question)`
*Same input guardrail, done once for both sub-calls.*
→ `ThreadPoolExecutor` runs `_run(query_vector_rag, ...)` and `_run(generate_cypher_query, ...)` **at the same time** → `vector_result`, `graph_result`
*Both full mode flows run in parallel, so the wait is the slower of the two, not both added together. `_run` catches each side's error instead of raising, and a failed side gets logged.*
→ if both failed → raise
*Only real failure case — nothing usable came back from either side.*
→ if one failed → return the other's answer directly (prefixed), **stop here**
*Degrades gracefully instead of discarding a working answer; no synthesis call is spent.*
→ if both succeeded → `_synthesize(question, vector_result["answer"], graph_result["answer"], domain_description)`
*Reconciles the two independent answers into one.*
  → `daily_limiter.check_and_increment()`
  *Third quota hit for a fully-successful hybrid call.*
  → `chain = prompt | llm | StrOutputParser()` → `chain.invoke(...)` → `result`
  *Asks the LLM to merge, or flag disagreement between, the two answers.*
  → returns synthesized text (or, if this call itself throws, falls back to both raw answers concatenated)
  *Never throws away two good answers just because the reconciliation step failed.*
→ return `{"answer": ..., "vector_chunks": ..., "graph_cypher_query": ...}`
*Returns the final answer plus whichever metadata each side actually produced.*
