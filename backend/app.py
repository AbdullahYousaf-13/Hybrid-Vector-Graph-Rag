"""
HTTP API in front of the RAG pipeline, which also serves the built frontend.

Local development (frontend runs separately on Vite, which proxies /api here):

    uvicorn backend.app:app --reload --port 8001

In production the frontend is built to frontend/dist and served from this same
process, so there is one origin and no CORS involved.
"""
import sys
import time
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from KG.config import load_neo4j_graph
from rag.vector_rag import query_vector_rag
from rag.graph_rag import generate_cypher_query
from rag.hybrid_rag import query_hybrid_rag

app = FastAPI()

# Only needed when the Vite dev server calls this directly rather than proxying.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["POST"],
    allow_headers=["*"],
)

graph, _, _ = load_neo4j_graph()

QUOTA_FILE = REPO_ROOT / ".daily_quota.json"
QUOTA_MAX = 250
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


class QueryRequest(BaseModel):
    question: str
    mode: str


def _read_quota() -> dict:
    try:
        data = json.loads(QUOTA_FILE.read_text())
        return {"used": data.get("count", 0), "max": QUOTA_MAX}
    except Exception:
        return {"used": 0, "max": QUOTA_MAX}


@app.get("/api/health")
def health():
    """Cheap liveness check: no LLM call, no quota cost. Used as Render's health check."""
    return {"status": "ok", "quota": _read_quota()}


@app.post("/api/query")
def query(request: QueryRequest):
    try:
        start = time.perf_counter()
        if request.mode == "vector":
            result = query_vector_rag(request.question, "Chunk", "Chunk", "text", "textEmbedding")
        elif request.mode == "graph":
            result = generate_cypher_query(request.question, graph)
        elif request.mode == "hybrid":
            result = query_hybrid_rag(request.question, graph)
        else:
            raise ValueError(f"Unknown mode: {request.mode!r}. Use 'vector', 'graph', or 'hybrid'.")
        elapsed = time.perf_counter() - start

        answer = result.pop("answer")
        return {
            "answer": answer,
            "details": result,
            "time_seconds": round(elapsed, 2),
            "quota": _read_quota(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal error while answering the question.")


# Mounted last so it never shadows /api/*. html=True serves index.html at "/".
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
