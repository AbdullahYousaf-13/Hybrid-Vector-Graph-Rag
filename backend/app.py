"""
Minimal HTTP API in front of the existing RAG pipeline.

Run from the repo root (not from backend/) so relative paths in the RAG
modules (.env, .daily_quota.json) resolve the same way they do for main.ipynb:

    uvicorn backend.app:app --reload --port 8001
"""
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from KG.config import load_neo4j_graph
from rag.vector_rag import query_vector_rag
from rag.graph_rag import generate_cypher_query
from rag.hybrid_rag import query_hybrid_rag

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["POST"],
    allow_headers=["*"],
)

graph, _, _ = load_neo4j_graph()

QUOTA_FILE = Path(__file__).resolve().parent.parent / ".daily_quota.json"
QUOTA_MAX = 250


class QueryRequest(BaseModel):
    question: str
    mode: str


def _read_quota() -> dict:
    try:
        data = json.loads(QUOTA_FILE.read_text())
        return {"used": data.get("count", 0), "max": QUOTA_MAX}
    except Exception:
        return {"used": 0, "max": QUOTA_MAX}


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
