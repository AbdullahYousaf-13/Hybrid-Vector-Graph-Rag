# Hybrid Vector + Graph RAG — Harry Potter Books

Ask natural-language questions about the Harry Potter book series (all 7
books, chunked by chapter) three complementary ways over a Neo4j knowledge
graph:

| Mode | Good at | Backed by |
|---|---|---|
| **Vector** | open-ended questions, facts stated in prose | Gemini embeddings over chunk text |
| **Graph** | precise structured questions (counts, relationships, "who is linked to X") | LLM-generated Cypher over the graph |
| **Hybrid** | everything above | calls both, reconciles the two answers with a third LLM call |

## Project structure

```
rag/            query-time retrieval: vector_rag.py, graph_rag.py, hybrid_rag.py
KG/             ingestion / knowledge-graph-building pipeline
backend/        FastAPI HTTP API in front of rag/
frontend/       Vite + React web UI
data/           source corpus (Book_*.json)
docs/           Living_Specs.md (full spec), Flow.md (step-by-step + diagrams),
                Guardrails.md (security/cost guardrails)
main.ipynb      notebook entry point for querying (mirrors backend/app.py)
prep.ipynb      one-time ingestion pipeline
```

## Setup

1. Clone the repo:
   ```
   git clone https://github.com/AbdullahYousaf-13/Hybrid-Vector-Graph-Rag.git
   cd Hybrid-Vector-Graph-Rag
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   pip install -r backend/requirements.txt
   ```
   Also run `pip install jupyter` if you want to use `main.ipynb` / `prep.ipynb`.

3. Create a `.env` file in the repo root:
   ```
   NEO4J_URI=...
   NEO4J_USERNAME=...
   NEO4J_PASSWORD=...
   NEO4J_DATABASE=...
   GEMINI_API_KEY=...
   ```

## Running it

**Web UI**
```
uvicorn backend.app:app --reload --port 8001     # terminal 1, from repo root
cd frontend && npm install && npm run dev         # terminal 2
```
Open `http://localhost:5173`, pick Vector / Graph / Hybrid, and ask a question.

**Notebook**
Open `main.ipynb` and run the cells — it calls the same `rag/` functions the
API uses.

Both paths share a single daily request quota (`.daily_quota.json`, 250/day)
and the same security/cost guardrails — see `docs/Guardrails.md`.

## Using your own data

The ingestion pipeline (`prep.ipynb` + `KG/`) and the entity/relationship
extraction prompts (`KG/entities.py`, `KG/normalize_relationships.py`) take a
`domain_description` parameter instead of a hardcoded corpus name, so the
same code can be pointed at a different text corpus. See `docs/Living_Specs.md`
§3 and §6 for the full ingestion pipeline layout.
