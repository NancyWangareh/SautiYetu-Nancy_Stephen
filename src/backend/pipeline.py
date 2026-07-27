"""
Pipeline orchestrator — parse → chunk → embed → store.

Run once (or via POST /api/ingest) to populate the vector database.
"""
import logging

from .embedder import EmbeddingService
from .ingestion import chunk_documents, parse_pdf
from .vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_ingestion(pdf_path: str | None = None) -> dict:
    """
    Full ingestion pipeline.

    1. Parse PDF → pages with text + tables
    2. Chunk pages → ~300–500 overlapping text chunks
    3. Load embedding model
    4. Embed all chunks in batches
    5. Store in Qdrant (local)

    Returns a stats dict with counts and timing.
    """
    import time

    t0 = time.perf_counter()

    # ── Step 1: Parse ────────────────────────────────────────────────
    logger.info("Step 1/5: Parsing PDF...")
    pages = parse_pdf(pdf_path)
    non_empty = [p for p in pages if p["text"].strip()]
    logger.info("Parsed %d pages (%d with text)", len(pages), len(non_empty))

    # ── Step 2: Chunk ────────────────────────────────────────────────
    logger.info("Step 2/5: Chunking text...")
    chunks = chunk_documents(pages)
    logger.info("Created %d chunks from %d pages", len(chunks), len(pages))

    if not chunks:
        return {"error": "No text extracted from PDF", "chunks": 0}

    # ── Step 3: Load embedder ────────────────────────────────────────
    logger.info("Step 3/5: Loading embedding model...")
    emb = EmbeddingService()
    texts = [c["text"] for c in chunks]

    # ── Step 4: Embed ────────────────────────────────────────────────
    logger.info("Step 4/5: Embedding %d chunks...", len(texts))
    embeddings = emb.embed_texts(texts, show_progress=True)
    logger.info("Embedded %d chunks (dim=%d)", len(embeddings), emb.vector_size)

    # ── Step 5: Store ────────────────────────────────────────────────
    logger.info("Step 5/5: Storing in Qdrant...")
    store = VectorStore()
    store.create_collection(emb.vector_size, force=True)
    count = store.upsert_chunks(chunks, embeddings)

    elapsed = round(time.perf_counter() - t0, 1)

    stats = {
        "pages_parsed": len(pages),
        "pages_with_text": len(non_empty),
        "chunks_created": len(chunks),
        "chunks_stored": count,
        "vector_size": emb.vector_size,
        "embedding_model": emb.model_name,
        "elapsed_seconds": elapsed,
    }

    logger.info("Ingestion complete! %s", stats)
    return stats


# ── CLI entry point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    pdf_arg = sys.argv[1] if len(sys.argv) > 1 else None
    stats = run_ingestion(pdf_arg)
    print("\n✅ Ingestion complete!")
    for k, v in stats.items():
        print(f"  {k}: {v}")
