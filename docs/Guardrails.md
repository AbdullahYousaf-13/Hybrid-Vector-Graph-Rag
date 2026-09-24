# Guardrails

Last updated: 2026-09-21

## Security guardrails — added

| Guardrail | Where | Why |
|---|---|---|
| Input validation | `rag/graph_rag.py`, `rag/vector_rag.py`, `rag/hybrid_rag.py` | reject empty questions and anything over 300 chars; strip `\r\n\t` so a question can't fake new prompt lines |
| Prompt-injection isolation | `rag/graph_rag.py`, `rag/vector_rag.py`, `rag/hybrid_rag.py` | user question wrapped in `<user_question>`/`<user_input>` tags + told to the LLM as untrusted data, so it can't be read as an instruction. `rag/hybrid_rag.py` extends this to the *answers themselves* — each side's answer is wrapped in its own `<text_search_answer>`/`<knowledge_graph_answer>` tag before the synthesis call, since either may echo corpus text |
| Entity-name allow-list | `rag/graph_rag.py` | LLM must match `Person`/`Event`/`Book` `.name` only against real values pulled from the graph, so it can't hallucinate a fake node to query. `Entity` nodes are deliberately excluded (too many to enumerate) — instead the prompt requires case-insensitive `CONTAINS` matching for those |
| Answer-relevance check before responding | `rag/graph_rag.py` (`qa_prompt`/`QA_TEMPLATE`) | `GraphCypherQAChain`'s *default* QA prompt only says "say you don't know if results are empty" — a non-empty but irrelevant `CONTAINS` match was getting reported as if it answered the question. `QA_TEMPLATE` requires the LLM to verify the returned rows actually, specifically answer the question first |
| Error / secret masking | `KG/config.py` | real Neo4j connection error (can contain URI/creds) is logged locally only; caller gets a generic message |
| Read-only enforcement on generated Cypher | `rag/graph_rag.py` | `graph.query` is wrapped for the duration of each call; `_enforce_readonly_cypher()` rejects any generated query containing `CREATE`/`DELETE`/`SET`/`DROP`/`MERGE`/`REMOVE`/`DETACH`/`ALTER` before it reaches Neo4j — closes the gap `allow_dangerous_requests=True` otherwise leaves open |

## Cost guardrails — added

| Guardrail | Where | Why |
|---|---|---|
| Retrieval cap `k=6` | `rag/vector_rag.py` | fewer chunks fetched per question = smaller prompt (raised from `k=3` once the corpus grew to 7 books) |
| Context truncation (8000 chars) | `rag/vector_rag.py` | caps how much chunk text gets sent to the LLM (raised from 3500 alongside `k`) |
| Shared persistent daily quota (`max_rpd=250`, a `(:DailyQuota {date, count})` node in Neo4j) | `rag/quota.py`, used by `rag/graph_rag.py`, `rag/vector_rag.py`, `rag/hybrid_rag.py` | one counter keyed by UTC date — survives restarts and Render redeploys, is shared by local runs and the deploy, and can't be doubled by alternating between paths. The increment locks the node before reading it and a uniqueness constraint on `date` stops duplicate nodes, so concurrent requests can't slip past the limit. The label is excluded from graph mode's schema prompt. **A single `query_hybrid_rag` call can cost up to 3 of the shared budget** (one per delegated call, plus one for its own synthesis call) — a real, non-trivial increase in quota pressure worth knowing about |
| Model `gemini-3.1-flash-lite` with `temperature=0` | `rag/graph_rag.py`, `rag/vector_rag.py`, `rag/hybrid_rag.py` | highest free-tier limits (15/min, 500/day) and, unlike `gemini-3.5-flash-lite`, it honors `temperature=0`, so repeated questions get consistent Cypher and answers |
| Row limit on generated Cypher | `rag/graph_rag.py` | same `graph.query` wrapper appends `LIMIT 25` via `_ensure_cypher_limit()` when the generated query has none, so an unbounded `MATCH (n) RETURN n` can't pull the whole graph into the summarization prompt |
| Skip synthesis on partial failure | `rag/hybrid_rag.py` | if only one of the two delegated calls succeeds, `query_hybrid_rag` returns that answer directly instead of spending a 3rd quota request reconciling a real answer against nothing |

### How the read-only + row-limit wrapper works

`GraphCypherQAChain.invoke(...)` generates and executes Cypher in one call —
there's no exposed hook to inspect the query before it runs. `generate_cypher_query()`
works around that by temporarily replacing `graph.query` with a wrapper that
runs both guardrail functions on every Cypher string right before it's sent to
Neo4j, then restores the original method in a `finally` block (so a blocked
query, or any other error, never leaves `graph` permanently patched for later
calls). See `rag/graph_rag.py` for the implementation.

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
~~Forcing Graph RAG to answer biographical/relational questions via chunk text~~ | **No longer applicable** — this was true when the corpus only had blanket, meaningless `RELATED_TO` edges (historical, pre-`Entity` work). Since `KG/entities.py` populated real `Entity` nodes and typed relationships (`FRIEND_OF`, `PARENT_OF`, etc.), Graph RAG genuinely does answer these questions now — see Living_Specs.md §7 and the known-limitations items in the 10-18 range for what's still imperfect about that data, which is a different (and real) set of concerns, not "this class of question is out of scope" |
