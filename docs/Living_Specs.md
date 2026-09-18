# Living Specification — Hybrid Vector + Graph RAG

> A "living" spec: it describes the system **as it is today**, not a frozen plan.
> Update it whenever behaviour, schema, or the stack changes.

Last updated: 2026-09-18

---

## 1. Purpose

Answer natural-language questions about the Harry Potter book series (all 7
books, chunked by chapter) two complementary ways:

| Path           | Good at                                                                    | Backed by                       |
| -------------- | -------------------------------------------------------------------------- | -------------------------------- |
| **Vector RAG** | open-ended questions, facts stated in prose                                | embeddings over chunk text      |
| **Graph RAG**  | precise structured questions (counts, relationships, "who is linked to X") | generated Cypher over the graph |

The end goal is a *hybrid* answer that uses both retrievers together. Today the
two paths are callable but invoked separately (see §8).

---

## 2. Stack

| Concern           | Choice                                                            | Notes                                                                                   |
| ------------------ | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| Graph DB          | **Neo4j Aura Free** (instance `HVGR`, id `3663f87a`)              | DB name **and** username are both `3663f87a`, not `neo4j` — set via `NEO4J_DATABASE`    |
| Embeddings        | **Gemini** `gemini-embedding-001`, 768 dims                       | computed in Python, L2-normalized; free tier                                            |
| Chat / Cypher LLM | **Gemini** `gemini-3.5-flash-lite`                                 | free tier, cheaper/faster tier chosen as a cost guardrail; ignores `temperature`; returns `content` as a list → needs `StrOutputParser` |
| Orchestration     | **LangChain v1.4** + `langchain-neo4j` + `langchain-google-genai` | `langchain.chains` no longer exists; chains built with LCEL (`prompt \| llm \| parser`)   |
| Chunking          | `RecursiveCharacterTextSplitter`                                  | `chunk_size=2000`, `chunk_overlap=200`                                                  |

Original upstream project used OpenAI throughout. It was migrated to Gemini
because the OpenAI account had no credits. No OpenAI dependency remains.

---

## 3. Repository layout

```
KG/
  config.py      load_neo4j_graph() -> (graph, GEMINI_API_KEY, None)
                 wraps the connection in try/except; logs the real error,
                 raises a sanitized RuntimeError externally (no secret leakage)
  chunking.py    split_data_from_file(path) -> list[chunk dict]
  kg.py          create_nodes, ingest_Chunks, create_relationship,
                 create_vector_index, embed_text
  entities.py    extract_entities(graph, api_key, batch_size, book_filter) ->
                 asks Gemini to pull characters/places/spells/etc. + relationships
                 out of each Chunk's text, MERGEs them as :Entity nodes linked to
                 their source Chunk via :MENTIONED_IN, with dynamic relationship
                 types between entities (e.g. :FRIEND_OF, :TEACHES).
                 Also: extract_relationships_for_category(graph, api_key, category,
                 flag_property, book_filter) -> generic, reusable targeted
                 extraction for one relationship category (e.g. family relations);
                 unlike extract_entities, records r.sourceChunk on every edge so
                 it can be verified against real evidence later. MERGE-only,
                 never deletes.
  normalize_relationships.py  normalize_relationships(graph, api_key) -> one-time
                 pass that asks Gemini to collapse near-duplicate relationship
                 types (e.g. OWNS/OWNER_OF/OWNED_BY/POSSESSES) into one canonical
                 type each, then rewrites the graph's edges accordingly.
                 Also: verify_relationships_with_source(graph, api_key, rel_types)
                 - the SAFE grounded verification pass, checks each edge's own
                 r.sourceChunk against real text. verify_relationships (no
                 _with_source) is DEPRECATED/UNSAFE - see Living_Specs.md §8
                 item 10 - do not use it.
  normalize_entities.py  normalize_entities(graph, api_key, limit) -> one-time
                 pass that merges alias duplicates of the same entity (e.g.
                 "Harry" + "Harry Potter") into one canonical :Entity node,
                 redirecting all of that node's relationships (any type/direction)
VectorRAG.py     query_vector_rag(question, index, label, text_prop, emb_prop)
                 input validation, prompt-injection isolation, retrieval/
                 context caps, daily quota tracking (see docs/Guardrails.md)
GraphRAG.py      generate_cypher_query(question, graph)
                 input validation, prompt-injection isolation, entity-name
                 allow-list, daily quota tracking, read-only + row-limit
                 enforcement on generated Cypher (via a graph.query wrapper)
prep.ipynb       one-time ingestion pipeline (§6)
main.ipynb       query entry point (§7)
KG/csv_to_json.py  one-off converter: data/harry_potter_books.csv -> data/Book_*.json
                   (groups CSV rows by book, then chapter; run once, not part of prep.ipynb)
KG/backup.py     export_graph / wipe_graph / import_graph — full graph JSON
                 backup so a corpus can be wiped and restored without
                 re-calling the embedding API
data/Book_*.json   source corpus: {chapter_name: chapter_text}, one file per book
data/harry_potter_books.csv  raw source (gitignored — regenerate Book_*.json with
                              KG/csv_to_json.py rather than committing the CSV)
docs/            Living_Specs.md (this file), Flow.md, Guardrails.md
```

Note: the file is `VectorRAG.py` (capital V) — imports must match that case
exactly (matters on Linux/CI, not just Windows).

---

## 4. Data model (current graph)

### Nodes

| Label     | Count                     | Key properties                                                                                                |
| --------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `Chunk`   | 3,565                     | `chunkId` (unique), `text`, `source` (= JSON chapter), `chunkSeqId`, `node_name`, `textEmbedding` (768-float) |
| `Section` | 200 (chapters, all books) | `type` (= JSON chapter key, e.g. `chap-1`), `parent_name`                                                     |
| `Book`    | 7                         | `name` — e.g. `Book_1_Philosopher_s_Stone` … `Book_7_Deathly_Hallows`                                         |
| `Entity`  | ~1,800 (after dedup)      | `name`, `type` (`Character`/`Location`/`Spell`/`Object`/`Creature`/`Organization`) |

`Book.name` values are **filename-derived ids** (underscores, no spaces), not the
human-readable book titles. `GraphRAG.py` injects the real list
(`_entity_name_catalog`, matching `Person`/`Event`/`Book`) into the Cypher
prompt as an allow-list so the LLM stops inventing slugs — this catalog does
**not** include `Entity` names (too many to usefully allow-list; the LLM relies
on `{schema}` plus a few-shot example instead, see §7).

### Relationships

| Pattern                                | Rule / source                                                        |
| ---------------------------------------- | ------------------------------------------------------------------------ |
| `(Section)-[:HAS_CHUNK]->(Chunk)`      | `s.type = c.source AND s.parent_name = c.node_name`                  |
| `(Book)-[:HAS_SECTION]->(Section)`     | `b.name = s.parent_name`                                              |
| `(Entity)-[:MENTIONED_IN]->(Chunk)`    | `KG/entities.py` — every entity found in a chunk links back to it     |
| `(Entity)-[:<DYNAMIC_TYPE>]->(Entity)` | `KG/entities.py` — Gemini-extracted relation per chunk, e.g. `FRIEND_OF`, `TEACHES`, `MEMBER_OF`, `OWNS`, `ENEMY_OF`; ~130 distinct canonical types after `normalize_relationships.py` collapsed ~430 raw ones |

Note: books aren't cross-linked to each other directly — any cross-book
connection between characters/places now flows through shared `Entity` nodes
(e.g. two `Book`s both having chunks that `MENTIONED_IN` the same `Entity`).

### Vector index

`CREATE VECTOR INDEX Chunk FOR (n:Chunk) ON (n.textEmbedding)` — 768 dims, cosine.

---

## 5. Guardrails

Implemented across `GraphRAG.py`, `VectorRAG.py`, `KG/config.py`. Full detail,
including what is **not** implemented yet, lives in **[Guardrails.md](Guardrails.md)**
— keep that file in sync whenever a guardrail is added or changed.

---

## 6. Ingestion pipeline (`prep.ipynb`)

0. `KG/csv_to_json.py` (run once, separately, before `prep.ipynb`) — converts
   `data/harry_potter_books.csv` into one `data/Book_*.json` per book, shaped
   as `{chapter_key: full_chapter_text}` to match what `split_data_from_file`
   expects (same `{section_name: text}` shape the old Wikipedia JSONs used).
1. `load_neo4j_graph()` — connect to Aura (now guarded, see §5).
2. `wipe_graph(graph, index_name="Chunk")` (`KG/backup.py`) — clears any
   previous corpus before re-ingesting (full swap, not additive).
3. For each file in `file_names` (the 7 `Book_*` basenames), printing
   per-book progress:
   - `split_data_from_file` — load JSON, split each chapter into ≤2000-char chunks.
   - `create_nodes` — MERGE the `Book` node + one `Section` per chapter key.
   - `ingest_Chunks` — MERGE a `Chunk` per chunk (idempotent on `chunkId`).
4. `create_relationship` × 2 — build the edges in §4 (`Section→Chunk`, `Book→Section`).
5. `create_vector_index` — create the 768-dim `Chunk` index.
6. `embed_text` — for every `Chunk` with `textEmbedding IS NULL`, run per-book
   (via `book_filter=name`) for visible progress:
   - embed text with Gemini (`RETRIEVAL_DOCUMENT`, 768 dims), L2-normalize,
   - write back with `db.create.setNodeVectorProperty`,
   - batched (64) with exponential backoff, honouring the API's `retryDelay`
     when present (free tier = 100 embed requests/min **and** 30K tokens/min
     **and** 1000 embed requests/day — a 7-book corpus is large enough to hit
     all three; see §8).
7. `extract_entities` (`KG/entities.py`), run per-book: for each `Chunk`, ask
   Gemini (`gemini-3.5-flash-lite`, separate quota pool from embedding) to
   return characters/places/spells/etc. plus relationships between them as
   JSON; MERGE the results as `Entity` nodes + `MENTIONED_IN` + dynamic
   relationship-type edges. Marks each processed chunk with
   `c.entitiesExtracted = true` so re-running only covers what's left.
8. `normalize_relationships` (`KG/normalize_relationships.py`), run once after
   extraction finishes for all books: collects every non-structural
   relationship type + its count, asks Gemini for a canonical-name mapping in
   one call, then rewrites (`MERGE` + `DELETE`) each old-type edge to its
   canonical type.
9. `normalize_entities` (`KG/normalize_entities.py`), run once: takes the
   top N (default 400) most-connected `Entity` nodes, asks Gemini to group
   alias variants of the same entity (e.g. "Harry" / "Harry Potter") under one
   canonical name, then redirects every relationship (any type, any direction)
   from each alias onto the canonical node and deletes the alias.
10. `extract_relationships_for_category` (`KG/entities.py`), run per-book for a
    targeted category (e.g. family relationships): re-scans every `Chunk`
    directly and, unlike step 7, records a `sourceChunk` property on every
    created edge — so later checks can verify against the *real* originating
    text instead of guessing. **Purely additive (`MERGE` only, never
    `DELETE`)** — safe to re-run, safe to interrupt. Marks chunks with a
    caller-supplied `flag_property` for resumability.
11. `verify_relationships_with_source` (`KG/normalize_relationships.py`), run
    once per relationship category after step 10: reads each edge's own
    `r.sourceChunk`, feeds that real passage to Gemini, and confirms,
    redirects, or deletes the edge based on that evidence. Edges with no
    `sourceChunk` (created before step 10 existed) are left completely
    untouched. **This does delete edges it can't confirm** — see §8 for the
    incident this replaced and why deletion here is scoped per-edge (matched
    by its own `sourceChunk`), not per name-pair.

Re-running steps 1-6 is safe: nodes MERGE on keys, embeddings skip
already-filled nodes — but **do not re-run the `wipe_graph` cell** after
embedding progress has started, or it erases everything embedded so far.
Steps 7-9 are also safe to re-run (idempotent MERGEs), but 8 and 9 are meant
to run once each, after extraction is fully done — running them mid-extraction
would only normalize a partial graph. Step 11 is the only step in this whole
pipeline that deletes graph data based on an LLM's judgment rather than a
fixed key — treat it with the same caution as `wipe_graph`.

**A deprecated, unsafe function exists in `KG/normalize_relationships.py`:
`verify_relationships` (without `_with_source`).** It grounds its check in an
*arbitrary* chunk where both entities happen to co-occur, not the chunk that
actually produced the claim — this caused a real data-loss incident (see §8,
item 10) where ~66% of edges were wrongly deleted because the arbitrary
grounding chunk didn't happen to restate the fact. **Do not use it.** It's
kept in the file only as a cautionary reference; `verify_relationships_with_source`
is the safe replacement.

---

## 7. Query paths

### `query_vector_rag` (`VectorRAG.py`)

```
question
  -> _validate_and_sanitize_question         # reject empty / >300 chars / strip \r\n\t
  -> Neo4jVector.from_existing_graph (Gemini query-embedding, 768d)
  -> retriever.invoke(question)               # top k=6 chunks by cosine (capped for cost)
  -> stuff chunk text into <context>, truncate to 8000 chars
  -> ChatPromptTemplate (<user_input> tag marks it untrusted) | gemini-3.5-flash-lite | StrOutputParser
  -> answer (wrapped to 60 cols)

daily_limiter.check_and_increment() runs before all of the above — reads/
writes .daily_quota.json (shared with GraphRAG.py), raises if today's count
has already reached max_rpd (250)
```

Answers strictly from retrieved chunk text ("say you don't know" otherwise).

### `generate_cypher_query` (`GraphRAG.py`)

```
question
  -> _validate_and_sanitize_question         # reject empty / >300 chars / strip \r\n\t
  -> _entity_name_catalog(graph)              # real Person/Event/Book names, used as allow-list
  -> PromptTemplate(schema, question wrapped in <user_question>, entity_names, few-shot examples)
  -> GraphCypherQAChain.from_llm(gemini-3.5-flash-lite, allow_dangerous_requests=True)
       -> graph.query wrapped: _enforce_readonly_cypher, _ensure_cypher_limit
       -> LLM writes Cypher -> guarded run on graph -> LLM summarizes rows
  -> answer (wrapped to 60 cols)
```

`Entity` names are **not** in the allow-list (too many to usefully enumerate), so the
Cypher prompt instead tells the LLM to match them with a case-insensitive
`CONTAINS` rather than exact equality (e.g. `WHERE toLower(e.name) CONTAINS
toLower("Ron")`), since questions rarely use the full stored name verbatim.
The prompt also explicitly tells the LLM to check **both** `PARENT_OF` and
`CHILD_OF` directions for any parent/child/son/daughter question (via `UNION`)
— extraction and normalization left the same real-world fact sometimes stored
under either type depending on the pair, so querying only one direction
silently misses results.

`daily_limiter.check_and_increment()` runs before all of the above, sharing
the same `.daily_quota.json` counter as `VectorRAG.py`. `graph.query` is
temporarily wrapped for the duration of `cypher_chain.invoke(...)` — every
generated Cypher string passes through `_enforce_readonly_cypher()` (raises
on write keywords) and `_ensure_cypher_limit()` (adds `LIMIT 25` if missing)
right before it reaches Neo4j, then the original method is restored in a
`finally` block. See [Guardrails.md](Guardrails.md) for why this shape was
needed (`GraphCypherQAChain` has no pre-exec hook).

---

## 8. Known limitations / tech debt

| #   | Issue                                                                                    | Impact                                    |
| --- | ------------------------------------------------------------------------------------------- | -------------------------------------------- |
| 1   | `RELATED_TO` (historical, Napoleon corpus) was created in both directions                | n/a for current `Book` corpus — no `RELATED_TO` edges exist now |
| 2   | `Person↔Person` / `Person↔Event` blanket edges (historical)                              | not used by the `Book` corpus; no `Book↔Book` equivalent exists |
| 3   | `main.ipynb` calls the two retrievers separately                                         | not a true hybrid answer                  |
| 4   | No `requirements.txt` / lockfile                                                         | environment not reproducible              |
| 5   | `id()` used in relationship Cypher (`prep.ipynb`)                                        | deprecation warnings; use `elementId()`   |
| 6   | Secrets (Gemini key, Neo4j password) appeared in a chat transcript                       | rotate when convenient                    |
| 7   | Full Harry Potter corpus (7 books, `chunk_size=2000`) is large enough to hit the Gemini free-tier's **daily** embed quota (1000 requests/day), not just RPM/TPM | initial ingestion embedding can take multiple days to fully complete on the free tier; resumable via `book_filter` + the `textEmbedding IS NULL` check, so partial progress is never lost |
| 8   | `normalize_entities.py` only checks the top 400 most-connected `Entity` nodes for alias duplicates | rare/low-mention aliases (e.g. `"Harry's dad"` instead of `"James Potter"`) can still slip through; re-run with a higher `limit` if more turn up |
| 9   | Entity extraction occasionally returns malformed JSON for a batch (LLM output truncation) | caught by the same generic retry/backoff loop as API errors, so it self-heals on retry, but a batch is fully redone rather than partially salvaged |
| 10  | **Incident:** the deprecated `verify_relationships` (grounds checks in an arbitrary co-mention chunk, not the real source) was run on 105 `PARENT_OF`/`CHILD_OF` edges and wrongly deleted 69 of them (~66%) — no backup existed, so they were unrecoverable | replaced by `verify_relationships_with_source`, which only checks edges with a real `r.sourceChunk` and deletes with per-edge precision; lost family edges were regenerated via `extract_relationships_for_category`. **Lesson: never run an LLM-driven `DELETE` pass without confirming a backup first** |
| 11  | No `gender` (or any attribute beyond `type`) is captured on `Entity` nodes | Graph RAG can't reliably filter "sons" vs "daughters" — it either returns all children regardless of sex, or gets lucky/unlucky based on whether the summarizing LLM happens to recall the character's gender from training data |
| 12  | Two different characters can share the exact same name in-universe (e.g. Tom Riddle Sr./Jr. — Jr. being Voldemort; Barty Crouch Sr./Jr.) | entity extraction has no disambiguation for this, so both collapse into one `Entity` node; produced literal self-loops (`X PARENT_OF X`) that had to be deleted, leaving those specific parent/child facts permanently unanswerable via Graph RAG (Vector RAG still handles them from raw text) |
| 13  | `verify_relationships_with_source`'s conservative grounding (only confirms what a single ~2000-char chunk states outright) has real recall loss | some genuinely true relationships (e.g. several of Arthur Weasley's other children) were dropped because their specific `sourceChunk` didn't restate the name explicitly; re-running `extract_relationships_for_category` can recover them |
| 14  | `GraphRAG.py`'s Cypher prompt now instructs checking both `PARENT_OF` and `CHILD_OF` directions for family questions, since the same fact can end up stored under either type depending on the pair | works, but is a prompt-level patch over an inconsistent underlying schema, not a real fix; a future normalization pass could collapse both into one canonical direction |
All items from the previous pass are resolved — see below.

Auth, call timeouts, Gemini-side error masking, audit logging, and forcing
Graph RAG to answer biographical/relational questions via chunk text were
considered and deliberately skipped (see Guardrails.md's "Considered, not
needed" table for why each one).

Resolved since the last pass: `vectorRAG.py` renamed to `VectorRAG.py` (import
casing now matches on every OS); stress-test question replaced with real
sample questions in `main.ipynb`; the old `SessionTokenBudget` (token-estimate
cap) was replaced with a `PersistentDailyQuotaTracker` — one shared counter
(`.daily_quota.json`, gitignored) read and written by both `GraphRAG.py` and
`VectorRAG.py`, `max_rpd=250`, survives a kernel/process restart;
`_enforce_readonly_cypher()` and `_ensure_cypher_limit()` are now actually
wired in via a `graph.query` wrapper (previously defined but dead code).

---

## 9. Roadmap

- [ ] Merge vector + graph context into a single hybrid prompt in `main.ipynb`.
- [ ] Derive `RELATED_TO` from co-occurrence in chunk text instead of all-pairs.
- [ ] Single-direction relationships + `elementId()`.
- [ ] `requirements.txt` (langchain, langchain-neo4j, langchain-google-genai, langchain-text-splitters, neo4j, python-dotenv, tqdm, numpy).
- [x] Rename `vectorRAG.py` → `VectorRAG.py` for portability.
- [ ] Add 10 evaluation questions with expected answers.
- [x] Replace estimated token-budget cap with a real request-count (RPD) guardrail.
- [x] Share one quota tracker between `GraphRAG.py` and `VectorRAG.py` instead of two independent ones.
- [x] Persist the daily counter (file) so it survives a kernel/process restart.
- [x] Wire `_enforce_readonly_cypher()` and `_ensure_cypher_limit()` into `generate_cypher_query()` via a `graph.query` wrapper.
