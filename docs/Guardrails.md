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
| Daily quota tracker (`max_rpd=4`, resets at midnight) | `GraphRAG.py`, `VectorRAG.py` | blocks further calls once today's request count hits the cap. `4` is a deliberately conservative test value — Gemini free tier for `gemini-3.5-flash-lite` is actually RPM 4 / TPM 6.69K / **RPD 7** (Tier 1 paid: 15 / 250K / 500) |
| Cheaper model `gemini-3.5-flash-lite` | `GraphRAG.py`, `VectorRAG.py` | lower cost/latency per call than the previous flash model |

## Not added yet

| Guardrail | Why it'd help |
|---|---|
| Read-only enforcement on generated Cypher | nothing stops the LLM from writing `CREATE`/`DELETE`/`SET` — `allow_dangerous_requests=True` has no check |
| Shared daily quota | `GraphRAG.py` and `VectorRAG.py` each track their own `max_rpd=4` — a session can spend 8/day by alternating, not 4 |
| Persistent quota (survives restart) | the counter is in-memory; restarting the kernel resets today's count back to 0 |
| Row limit (`LIMIT`) on generated Cypher | an unbounded query like `MATCH (n) RETURN n` isn't capped — harmless at 166 nodes today, matters once the graph grows |

## Considered, not needed for this project

Deliberately skipped — single-user personal/demo project, not deployed for
others to call. Revisit if that changes.

| Guardrail | Why it's skipped |
|---|---|
| Auth / per-user identity | only you call these functions |
| Timeouts on LLM/DB calls | no concurrent/untrusted callers to protect against a hang |
| Gemini-side error masking | errors only ever surface to you locally, not to another user |
| Audit log of question → Cypher → result | no abuse surface to review; you're the only caller |
