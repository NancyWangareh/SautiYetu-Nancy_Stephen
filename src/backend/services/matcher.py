"""
Match citizen requests against the budget via Qdrant vector search.
No Pinecone. No DeepSeek reasoning step.
"""
import json
import logging
from typing import Optional

from .embedder import EmbeddingService
from .vector_store import VectorStore

logger = logging.getLogger(__name__)

MATCH_THRESHOLDS = {
    "matched": 0.75,
    "partial": 0.50,
}


async def match_citizen_to_budget(
    citizen_text: str,
    predicted_sector: str,
    predicted_sub_sector: str,
    ward: Optional[str] = None,
    document_id: Optional[str] = None,
) -> dict:
    """
    1. Embed citizen input
    2. Search Qdrant for similar budget chunks
    3. Return best match with alternatives
    """
    try:
        embedder = EmbeddingService()
        query_vector = embedder.embed_query(citizen_text)

        store = VectorStore()
        if not store.collection_exists():
            return _no_match("Budget index not yet available. Please upload a budget PDF first.")

        hits = store.search(query_vector, top_k=5, document_id=document_id)

        if not hits or hits[0]["score"] < MATCH_THRESHOLDS["partial"]:
            return _no_match("No matching budget provision found.")

        best = hits[0]
        score = best["score"]

        if score >= MATCH_THRESHOLDS["matched"]:
            status = "matched"
            label = "Found"
        else:
            status = "partial"
            label = "Partial match"

        excerpt = best["text"].strip()[:300]
        page = best.get("page_number", "?")
        budget_result = f"[{label} · p.{page} · {score:.0%}] {excerpt}"

        alternatives = json.dumps([
            {
                "text": h.get("text", "")[:200],
                "page": h.get("page_number"),
                "score": round(h.get("score", 0), 4),
            }
            for h in hits[1:4]
        ])

        return {
            "matched_line_id": best.get("chunk_id", ""),
            "matched_sector": predicted_sector,
            "matched_description": best.get("text", "")[:500],
            "matched_amount_ksh": None,
            "matched_amount_requested_ksh": None,
            "budget_result": budget_result,
            "status": status,
            "similarity_score": round(score, 4),
            "alternative_matches": alternatives,
        }

    except Exception as e:
        logger.error("Match error: %s", e)
        return _no_match(f"Search error: {str(e)[:100]}")


def _no_match(reason: str) -> dict:
    return {
        "matched_line_id": None,
        "matched_sector": "Uncategorized",
        "matched_description": reason,
        "matched_amount_ksh": None,
        "matched_amount_requested_ksh": None,
        "budget_result": f"No match: {reason}",
        "status": "ignored",
        "similarity_score": 0.0,
        "alternative_matches": "[]",
    }