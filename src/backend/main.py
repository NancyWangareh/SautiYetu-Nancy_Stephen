"""
FastAPI application — RAG backend for budget PDF semantic search.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .embedder import EmbeddingService
from .vector_store import VectorStore


# ── Globals (lazy-initialized on first request) ──────────────────────────
embedder: EmbeddingService | None = None
store: VectorStore | None = None


def get_embedder() -> EmbeddingService:
    global embedder
    if embedder is None:
        embedder = EmbeddingService()
    return embedder


def get_store() -> VectorStore:
    global store
    if store is None:
        store = VectorStore()
    return store


# ── FastAPI app ──────────────────────────────────────────────────────────
app = FastAPI(
    title="SautiYetu RAG API",
    description="Semantic search over Nairobi County budget documents.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    """Return service status."""
    return {
        "status": "ok",
        "embedder_loaded": embedder is not None and embedder.model is not None,
        "store_ready": store is not None and store.client is not None,
    }


@app.post("/api/search")
def search(payload: dict):
    """
    Semantic search over budget document chunks.

    Expects: { "query": "maternity health budget", "top_k": 5 }
    Returns: { "results": [...], "query_time_ms": 123 }
    """
    import time

    query = payload.get("query", "").strip()
    if not query:
        return {"results": [], "query_time_ms": 0}

    top_k = payload.get("top_k", 5)

    t0 = time.perf_counter()
    emb = get_embedder()
    vec = get_store()

    query_embedding = emb.embed_query(query)
    hits = vec.search(query_embedding, top_k=top_k)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    return {"results": hits, "query_time_ms": elapsed_ms}


@app.post("/api/ingest")
def ingest(payload: dict | None = None):
    """
    (Re)ingest the budget PDF — parse, chunk, embed, store.

    Optional payload: { "pdf_path": "/absolute/path/to/budget.pdf" }
    """
    from .pipeline import run_ingestion

    pdf_path = (payload or {}).get(
        "pdf_path",
        None,
    )
    stats = run_ingestion(pdf_path)
    return {"status": "completed", **stats}
