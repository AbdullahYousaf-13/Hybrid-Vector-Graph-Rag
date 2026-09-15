# Guardrails

Last updated: 2026-09-15

## Security guardrails — added

| Guardrail | Where | Why |
|---|---|---|
| Input validation | `GraphRAG.py`, `VectorRAG.py` | reject empty questions and anything over 300 chars; strip `\r\n\t` so a question can't fake new prompt lines |
| Prompt-injection isolation | `GraphRAG.py`, `VectorRAG.py` | user question wrapped in `<user_question>`/`<user_input>` tags + told to the LLM as untrusted data, so it can't be read as an instruction |
| Entity-name allow-list | `GraphRAG.py` | LLM must match `.name` only against real Person/Event names pulled from the graph, so it can't hallucinate a fake node to query |
| Error / secret masking | `KG/config.py` | real Neo4j connection error (can contain URI/creds) is logged locally only; caller gets a generic message |

## Cost guardrails — added

| Guardrail | Where | Why |
|---|---|---|
| Retrieval cap `k=3` | `VectorRAG.py` | fewer chunks fetched per question = smaller prompt |
| Context truncation (3500 chars) | `VectorRAG.py` | caps how much chunk text gets sent to the LLM |
| Shared persistent daily quota (`max_rpd=250`, backed by `.daily_quota.json`) | `GraphRAG.py`, `VectorRAG.py` | one counter, read/written by both files, keyed by date — survives a kernel restart and can't be doubled by alternating between the two RAG paths. `.daily_quota.json` is gitignored (it's runtime state, not source) |
| Cheaper model `gemini-3.5-flash-lite` | `GraphRAG.py`, `VectorRAG.py` | lower cost/latency per call than the previous flash model |

## ⚠️ Defined but not enforced (looks added, isn't)

`GraphRAG.py` defines `_enforce_readonly_cypher()` and `_ensure_cypher_limit()`
— they read like the read-only and row-limit guardrails below, but **neither
function is ever called** in `generate_cypher_query()`. The generated Cypher
runs unmodified and unchecked; confirmed live in `main.ipynb`, where the
executed query has no `LIMIT` despite `_ensure_cypher_limit` existing to add
one. Treat both as **not implemented** until they're actually wired into
`generate_cypher_query()` (call `_enforce_readonly_cypher` and
`_ensure_cypher_limit` on `response`'s generated query before/around
execution — LangChain's `GraphCypherQAChain` doesn't expose a clean pre-exec
hook for this today, which is likely why they were left unwired).

## Not added yet

| Guardrail | Why it'd help |
|---|---|
| Read-only enforcement on generated Cypher (wire up `_enforce_readonly_cypher`) | nothing stops the LLM from writing `CREATE`/`DELETE`/`SET` — `allow_dangerous_requests=True` has no check, and the function meant to check it isn't called |
| Row limit on generated Cypher (wire up `_ensure_cypher_limit`) | an unbounded query like `MATCH (n) RETURN n` isn't capped — harmless at 166 nodes today, matters once the graph grows, and the function meant to add `LIMIT` isn't called |

## Considered, not needed for this project

Deliberately skipped — single-user personal/demo project, not deployed for
others to call. Revisit if that changes.

| Guardrail | Why it's skipped |
|---|---|
| Auth / per-user identity | only you call these functions |
| Timeouts on LLM/DB calls | no concurrent/untrusted callers to protect against a hang |
| Gemini-side error masking | errors only ever surface to you locally, not to another user |
| Audit log of question → Cypher → result | no abuse surface to review; you're the only caller |
