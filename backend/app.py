import sys
import time
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from KG.config import load_neo4j_graph
from rag.vector_rag import get_vector_store, query_vector_rag
from rag.graph_rag import generate_cypher_query
from rag.hybrid_rag import query_hybrid_rag
from rag.quota import QuotaExceededError, daily_limiter

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["POST"],
    allow_headers=["*"],
)

graph, _, _ = load_neo4j_graph()

try:
    get_vector_store("Chunk", "Chunk", "text", "textEmbedding")
except Exception:
    logging.getLogger("uvicorn.error").exception("Vector store warm-up failed; will retry on first query")

FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


class QueryRequest(BaseModel):
    question: str
    mode: str


def _read_quota() -> dict:
    try:
        return daily_limiter.usage()
    except Exception:
        logging.getLogger("uvicorn.error").exception("Could not read the daily quota")
        return {"used": None, "max": daily_limiter.max_rpd}


def _gemini_busy(error: BaseException) -> bool:
    while error is not None:
        text = str(error)
        if "UNAVAILABLE" in text or "RESOURCE_EXHAUSTED" in text:
            return True
        error = error.__cause__ or error.__context__
    return False


@app.get("/api/health")
def health():
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
    except QuotaExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        logging.getLogger("uvicorn.error").exception("Query failed (mode=%s)", request.mode)
        if _gemini_busy(e):
            raise HTTPException(
                status_code=503,
                detail="Gemini is overloaded or rate-limiting requests right now.",
            )
        raise HTTPException(status_code=500, detail="Internal error while answering the question.")


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
