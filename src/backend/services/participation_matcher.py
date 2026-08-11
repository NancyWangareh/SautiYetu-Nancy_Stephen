"""
Participation Matcher — ingests public participation data into Qdrant
and finds similar community-raised concerns for incoming citizen inputs.
"""

import logging

from .embedder import EmbeddingService
from .participation_parser import extract_points, parse_participation_pdf
from .vector_store import PARTICIPATION_COLLECTION, VectorStore

logger = logging.getLogger(__name__)

PARTICIPATION_THRESHOLD = 0.70
BOOST_MULTIPLIER = 0.20
TOP_K_PARTICIPATION = 5


def ingest_participation(pdf_path: str | None = None) -> dict:
    """
    Full participation ingestion: parse → extract → embed → store in Qdrant.
    """
    import time

    t0 = time.perf_counter()

    logger.info("Parsing participation PDF...")
    pages = parse_participation_pdf(pdf_path)
    logger.info("Parsed %d pages", len(pages))

    logger.info("Extracting citizen input points...")
    points = extract_points(pages)
    logger.info("Extracted %d participation points", len(points))

    if not points:
        return {"error": "No participation points extracted", "points": 0}

    logger.info("Embedding %d points...", len(points))
    emb = EmbeddingService()
    texts = [p["text"] for p in points]
    embeddings = emb.embed_texts(texts, show_progress=True)
    logger.info("Embedded %d points (dim=%d)", len(embeddings), emb.vector_size)

    logger.info("Storing in Qdrant collection '%s'...", PARTICIPATION_COLLECTION)
    store = VectorStore()

    chunks = [
        {
            "chunk_id": p["point_id"],
            "text": p["text"],
            "page_number": p.get("page_number", 0),
            "metadata": {
                "section": p.get("section", ""),
                "char_count": p.get("char_count", 0),
                "source": "public_participation",
            },
        }
        for p in points
    ]

    store.create_collection(emb.vector_size, force=True, name=PARTICIPATION_COLLECTION)
    count = store.upsert_chunks(chunks, embeddings, collection=PARTICIPATION_COLLECTION)

    elapsed = round(time.perf_counter() - t0, 1)

    return {
        "pages_parsed": len(pages),
        "points_extracted": len(points),
        "points_stored": count,
        "vector_size": emb.vector_size,
        "embedding_model": emb.model_name,
        "elapsed_seconds": elapsed,
    }


def find_similar_participation(
    query_text: str,
    embedder: EmbeddingService | None = None,
    store: VectorStore | None = None,
) -> dict:
    """
    Search for public participation points semantically similar to a citizen query.
    Returns { hasMatch, boostFactor, bestScore, matches: [...] }
    """
    if embedder is None:
        embedder = EmbeddingService()
    if store is None:
        store = VectorStore()

    if not store.participation_collection_exists():
        return {"hasMatch": False, "boostFactor": 0.0, "matches": []}

    q_emb = embedder.embed_query(query_text)
    hits = store.search(
        q_emb,
        top_k=TOP_K_PARTICIPATION,
        score_threshold=PARTICIPATION_THRESHOLD,
        collection=PARTICIPATION_COLLECTION,
    )

    if not hits:
        return {"hasMatch": False, "boostFactor": 0.0, "matches": []}

    matches = []
    max_score = 0.0
    for hit in hits:
        score = hit.get("score", 0)
        if score > max_score:
            max_score = score
        matches.append({
            "score": score,
            "text": hit.get("text", ""),
            "section": (hit.get("metadata") or {}).get("section", ""),
            "page_number": hit.get("page_number", 0),
            "point_id": hit.get("chunk_id", ""),
        })

    boost_factor = round(max_score * BOOST_MULTIPLIER, 4)

    return {
        "hasMatch": True,
        "boostFactor": boost_factor,
        "bestScore": max_score,
        "matches": matches,
    }