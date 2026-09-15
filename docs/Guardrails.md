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
| Daily quota tracker (`max_rpd=4`, resets at midnight) | `GraphRAG.py`, `VectorRAG.py` | blocks further calls once today's request count hits the cap, so a session can't blow past Gemini's real daily free-tier limit |
| Cheaper model `gemini-3.5-flash-lite` | `GraphRAG.py`, `VectorRAG.py` | lower cost/latency per call than the previous flash model |

## Not added yet

| Guardrail | Why it'd help |
|---|---|
| Read-only enforcement on generated Cypher | nothing stops the LLM from writing `CREATE`/`DELETE`/`SET` — `allow_dangerous_requests=True` has no check |
| Shared daily quota | `GraphRAG.py` and `VectorRAG.py` each track their own `max_rpd=4` — a session can spend 8/day by alternating, not 4 |
| Persistent quota (survives restart) | the counter is in-memory; restarting the kernel resets today's count back to 0 |
| Confirm `max_rpd=4` is the right number | Gemini's free-tier RPD for `gemini-3.5-flash-lite` is 7, not 4 — 4 matches its RPM instead; worth checking this was intentional |
| Auth / per-user identity | anyone calling the functions has full access, no way to scope limits per user |
| Auth / per-user identity | anyone calling the functions has full access, no way to scope limits per user |
| Row limit (`LIMIT`) on generated Cypher | an unbounded query like `MATCH (n) RETURN n` isn't capped |
| Timeouts on LLM/DB calls | a hung request currently hangs the whole call |
| Gemini-side error masking | unlike Neo4j, Gemini API errors surface raw (rate limit, auth, etc.) |
| Audit log of question → Cypher → result | no record kept for debugging or abuse review |
