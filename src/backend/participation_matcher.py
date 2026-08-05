"""
Participation Matcher — ingests public participation data and finds
similar community-raised concerns for incoming citizen inputs.

Two roles:
  1. Ingestion: parse → embed → store participation points in Qdrant
  2. Matching: given a citizen query, find similar points + compute a boost score

Algorithm: Weighted score fusion with participation boosting.

  Given citizen input Q:
    1. Embed Q
    2. Search participation collection for top-k similar points
    3. For each hit with score >= PARTICIPATION_THRESHOLD (0.70):
       - Record as a "participation match"
    4. The participation boost factor α is computed as:
         α = max(participation_scores) * BOOST_MULTIPLIER
       where BOOST_MULTIPLIER = 0.20
    5. This boost is added to the budget match score during re-ranking

This ensures citizen inputs that echo already-documented community concerns
are highlighted and prioritized in the matching results.
"""
import logging

from .embedder import EmbeddingService
from .participation_parser import extract_points, parse_participation_pdf
from .vector_store import PARTICIPATION_COLLECTION, VectorStore

logger = logging.getLogger(__name__)

# ── Thresholds ───────────────────────────────────────────────────────────
PARTICIPATION_THRESHOLD = 0.70   # minimum cosine similarity to consider a match
BOOST_MULTIPLIER = 0.20          # max boost applied to budget score
TOP_K_PARTICIPATION = 5          # how many participation hits to retrieve


def ingest_participation(pdf_path: str | None = None) -> dict:
    """
    Full participation ingestion pipeline:
      1. Parse participation PDF → pages
      2. Extract individual citizen concern "points"
      3. Embed each point
      4. Store in Qdrant (participation_chunks collection)

    Returns stats dict.
    """
    import time

    t0 = time.perf_counter()

    # ── Step 1: Parse ────────────────────────────────────────────────
    logger.info("Step 1/4: Parsing participation PDF...")
    pages = parse_participation_pdf(pdf_path)
    logger.info("Parsed %d pages", len(pages))

    # ── Step 2: Extract points ───────────────────────────────────────
    logger.info("Step 2/4: Extracting citizen input points...")
    points = extract_points(pages)
    logger.info("Extracted %d individual participation points", len(points))

    if not points:
        return {"error": "No participation points extracted from PDF", "points": 0}

    # ── Step 3: Embed ────────────────────────────────────────────────
    logger.info("Step 3/4: Embedding %d points...", len(points))
    emb = EmbeddingService()
    texts = [p["text"] for p in points]
    embeddings = emb.embed_texts(texts, show_progress=True)
    logger.info("Embedded %d points (dim=%d)", len(embeddings), emb.vector_size)

    # ── Step 4: Store ────────────────────────────────────────────────
    logger.info("Step 4/4: Storing in Qdrant collection '%s'...", PARTICIPATION_COLLECTION)
    store = VectorStore()

    # Build chunk dicts compatible with VectorStore.upsert_chunks
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

    stats = {
        "pages_parsed": len(pages),
        "points_extracted": len(points),
        "points_stored": count,
        "vector_size": emb.vector_size,
        "embedding_model": emb.model_name,
        "elapsed_seconds": elapsed,
    }

    logger.info("Participation ingestion complete! %s", stats)
    return stats


def find_similar_participation(
    query_text: str,
    embedder: EmbeddingService | None = None,
    store: VectorStore | None = None,
) -> dict:
    """
    Search for public participation points semantically similar to a citizen query.

    Returns:
        {
            "hasMatch": bool,
            "boostFactor": float,          # α — boost to apply to budget score
            "matches": [
                {
                    "score": 0.85,
                    "text": "Residents requested a new maternity wing...",
                    "section": "Health",
                    "page_number": 3,
                    "point_id": "PT-042",
                },
                ...
            ],
        }
    """
    if embedder is None:
        embedder = EmbeddingService()
    if store is None:
        store = VectorStore()

    # If the participation collection doesn't exist yet, no matches possible
    if not store.participation_collection_exists():
        return {"hasMatch": False, "boostFactor": 0.0, "matches": []}

    # Embed the citizen query
    q_emb = embedder.embed_query(query_text)

    # Search participation collection
    hits = store.search(
        q_emb,
        top_k=TOP_K_PARTICIPATION,
        score_threshold=PARTICIPATION_THRESHOLD,
        collection=PARTICIPATION_COLLECTION,
    )

    if not hits:
        return {"hasMatch": False, "boostFactor": 0.0, "matches": []}

    # Build match list
    matches = []
    max_score = 0.0

    for hit in hits:
        score = hit.get("score", 0)
        if score > max_score:
            max_score = score

        matches.append(
            {
                "score": score,
                "text": hit.get("text", ""),
                "section": (hit.get("metadata") or {}).get("section", ""),
                "page_number": hit.get("page_number", 0),
                "point_id": hit.get("chunk_id", ""),
            }
        )

    # Compute boost factor: proportional to best participation match score
    boost_factor = round(max_score * BOOST_MULTIPLIER, 4)

    return {
        "hasMatch": True,
        "boostFactor": boost_factor,
        "bestScore": max_score,
        "matches": matches,
    }
