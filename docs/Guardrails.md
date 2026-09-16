# Guardrails

Last updated: 2026-09-16

## Security guardrails — added

| Guardrail | Where | Why |
|---|---|---|
| Input validation | `GraphRAG.py`, `VectorRAG.py` | reject empty questions and anything over 300 chars; strip `\r\n\t` so a question can't fake new prompt lines |
| Prompt-injection isolation | `GraphRAG.py`, `VectorRAG.py` | user question wrapped in `<user_question>`/`<user_input>` tags + told to the LLM as untrusted data, so it can't be read as an instruction |
| Entity-name allow-list | `GraphRAG.py` | LLM must match `.name` only against real Person/Event names pulled from the graph, so it can't hallucinate a fake node to query |
| Error / secret masking | `KG/config.py` | real Neo4j connection error (can contain URI/creds) is logged locally only; caller gets a generic message |
| Read-only enforcement on generated Cypher | `GraphRAG.py` | `graph.query` is wrapped for the duration of each call; `_enforce_readonly_cypher()` rejects any generated query containing `CREATE`/`DELETE`/`SET`/`DROP`/`MERGE`/`REMOVE`/`DETACH`/`ALTER` before it reaches Neo4j — closes the gap `allow_dangerous_requests=True` otherwise leaves open |

## Cost guardrails — added

| Guardrail | Where | Why |
|---|---|---|
| Retrieval cap `k=3` | `VectorRAG.py` | fewer chunks fetched per question = smaller prompt |
| Context truncation (3500 chars) | `VectorRAG.py` | caps how much chunk text gets sent to the LLM |
| Shared persistent daily quota (`max_rpd=250`, backed by `.daily_quota.json`) | `GraphRAG.py`, `VectorRAG.py` | one counter, read/written by both files, keyed by date — survives a kernel restart and can't be doubled by alternating between the two RAG paths. `.daily_quota.json` is gitignored (it's runtime state, not source) |
| Cheaper model `gemini-3.5-flash-lite` | `GraphRAG.py`, `VectorRAG.py` | lower cost/latency per call than the previous flash model |
| Row limit on generated Cypher | `GraphRAG.py` | same `graph.query` wrapper appends `LIMIT 25` via `_ensure_cypher_limit()` when the generated query has none, so an unbounded `MATCH (n) RETURN n` can't pull the whole graph into the summarization prompt |

### How the read-only + row-limit wrapper works

`GraphCypherQAChain.invoke(...)` generates and executes Cypher in one call —
there's no exposed hook to inspect the query before it runs. `generate_cypher_query()`
works around that by temporarily replacing `graph.query` with a wrapper that
runs both guardrail functions on every Cypher string right before it's sent to
Neo4j, then restores the original method in a `finally` block (so a blocked
query, or any other error, never leaves `graph` permanently patched for later
calls). See `GraphRAG.py` for the implementation.

## Not added yet

Nothing outstanding from the earlier list — see "Considered, not needed for
this project" below for items deliberately skipped instead.

## Considered, not needed for this project

Deliberately skipped — single-user personal/demo project, not deployed for
others to call. Revisit if that changes.

| Guardrail | Why it's skipped |
|---|---|
| Auth / per-user identity | only you call these functions |
| Timeouts on LLM/DB calls | no concurrent/untrusted callers to protect against a hang |
| Gemini-side error masking | errors only ever surface to you locally, not to another user |
| Audit log of question → Cypher → result | no abuse surface to review; you're the only caller |
| Forcing Graph RAG to answer biographical/relational questions (e.g. "who is X's father") via chunk text | not a graph fact — `RELATED_TO` carries no semantic meaning, so this is a data-model gap, not something a guardrail or prompt patch should paper over. Those questions belong to Vector RAG, which already answers them correctly. See Living_Specs.md known limitation #2 |
