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
frontend/       Vite + React + Tailwind web UI (self-hosted fonts/images in public/)
data/           source corpus (Book_*.json)
docs/           Living_Specs.md (full spec), Flow.md (step-by-step + diagrams),
                Guardrails.md (security/cost guardrails), QA_Prep.md (function-level
                call-chain reference for rag/ and KG/)
main.ipynb      notebook entry point for querying (mirrors backend/app.py)
prep.ipynb      one-time ingestion pipeline
Dockerfile      builds the frontend, then serves it from the API (one service)
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
Vite proxies `/api` to port 8001, so the frontend calls the same relative path
it uses in production.

**Notebook**
Open `main.ipynb` and run the cells — it calls the same `rag/` functions the
API uses.

Both paths share a single daily request quota (250/day, stored as a `DailyQuota`
node in Neo4j so it survives restarts and redeploys; resets at midnight UTC)
and the same security/cost guardrails — see `docs/Guardrails.md`.

## Deploying (Render)

One Docker web service runs everything: the image builds the frontend with Node,
then serves `frontend/dist` from FastAPI, so there is a single origin and no CORS.

1. Push to GitHub, then in Render: **New > Web Service**, pick this repo. It
   detects the `Dockerfile`; `render.yaml` sets the plan and health check path.
2. Add the environment variables from your `.env` (`NEO4J_URI`,
   `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `GEMINI_API_KEY`).
   `load_dotenv()` is a no-op without a `.env` file, so the real environment is
   used. Never commit `.env`.
3. Health check path is `/api/health` (no LLM call, no quota cost).

Run the same image locally with `docker build -t hogwarts-archive . && docker run
-p 8000:8000 --env-file .env hogwarts-archive`.

Three things to expect on the free tier:

- **The service sleeps after ~15 minutes idle.** The first visit then pays a cold
  start, and this app is slow to boot (LangChain imports plus a Neo4j connection
  at startup) before it even begins answering.
- **Neo4j Aura Free pauses after ~3 days of inactivity.** The deployed app will
  error until you resume the instance from the Aura console.
- **Anyone with the URL spends your Gemini quota.** The 250/day guardrail is shared
  by local runs and the deploy, and a hybrid question costs 3 requests. Gemini's free
  tier also allows only 15 calls per minute, and a hybrid question makes 4.

**Keeping it awake:** `.github/workflows/keep-awake.yml` pings `/api/health` every
10 minutes so the free service doesn't sleep (and Aura Free doesn't pause). It
does nothing until you add the site URL as a repository variable: Settings >
Secrets and variables > Actions > Variables > `RENDER_URL`
(e.g. `https://your-service.onrender.com`). GitHub can delay scheduled runs by a
few minutes, so an occasional cold start is still possible.

## Using your own data

The ingestion pipeline (`prep.ipynb` + `KG/`) and the entity/relationship
extraction prompts (`KG/entities.py`, `KG/normalize_relationships.py`) take a
`domain_description` parameter instead of a hardcoded corpus name, so the
same code can be pointed at a different text corpus. See `docs/Living_Specs.md`
§3 and §6 for the full ingestion pipeline layout.
