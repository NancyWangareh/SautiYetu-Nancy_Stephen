"""Budget matcher — semantic search against Qdrant. No fallback."""

import json
import logging
from .embedder import EmbeddingService
from .vector_store import VectorStore
from .simplifier import simplify_with_llm, simplify_budget_line
from ..config import settings

logger = logging.getLogger(__name__)

MATCH_THRESHOLDS = {"matched": 0.80, "partial": 0.70}


class MatcherService:
    def __init__(self, embedder: EmbeddingService, store: VectorStore):
        self.embedder = embedder
        self.store = store

    async def match(
        self,
        citizen_text: str,
        sector: str,
        sub_sector: str,
        ward: str | None = None,
        participation_boost: float = 0.0,
        document_id: str | None = None,
        collection: str = "budget_proposed",
    ) -> dict:
        if not self.store.collection_exists(collection):
            raise RuntimeError(
                f"Budget index '{collection}' not available. "
                "Upload a budget PDF first via /api/budget/upload."
            )

        # Build enriched query
        if sector and sector != "Uncategorized":
            enriched_query = f"{sector}: {sub_sector}. {citizen_text}"
        else:
            enriched_query = citizen_text

        # Semantic search
        query_vector = self.embedder.embed_query(enriched_query)
        hits = self.store.search(query_vector, top_k=5, collection=collection)

        if not hits or hits[0]["score"] < MATCH_THRESHOLDS["partial"]:
            return self._no_match()

        best = hits[0]
        base_score = best["score"]
        boosted_score = min(0.99, base_score + participation_boost)

        # Determine status from boosted score
        if boosted_score >= MATCH_THRESHOLDS["matched"]:
            status = "matched"
            label = "Found"
        elif boosted_score >= MATCH_THRESHOLDS["partial"]:
            status = "partial"
            label = "Partial match"
        else:
            status = "ignored"
            label = "No match"

        excerpt = best["text"].strip()[:300]
        page = best.get("page_number", "?")

        # Simplify
        budget_text = best.get("text", "")
        simplified = simplify_with_llm(budget_text) if settings.DEEPSEEK_API_KEY else simplify_budget_line(budget_text)

        # Alternative matches
        alternatives = json.dumps([
            {"text": h.get("text", "")[:200], "page": h.get("page_number"), "score": round(h.get("score", 0), 4)}
            for h in hits[1:4]
        ])

        return {
            "matched_line_id": best.get("chunk_id", ""),
            "matched_sector": sector,
            "matched_description": best.get("text", "")[:500],
            "matched_amount_ksh": None,
            "source_page": page,
            "budget_result": f"[{label} · p.{page} · {boosted_score:.0%}] {excerpt}",
            "status": status,
            "similarity_score": round(base_score, 4),
            "boosted_score": round(boosted_score, 4),
            "simplified": simplified.get("simplified", ""),
            "key_points": simplified.get("key_points", []),
            "category": simplified.get("category", ""),
            "alternative_matches": alternatives,
        }

    def _no_match(self) -> dict:
        return {
            "matched_line_id": None,
            "matched_sector": "",
            "matched_description": "No matching budget provision found.",
            "matched_amount_ksh": None,
            "source_page": None,
            "budget_result": "No matching budget provision found in the enacted budget.",
            "status": "ignored",
            "similarity_score": 0.0,
            "boosted_score": 0.0,
            "simplified": "",
            "key_points": [],
            "category": "",
            "alternative_matches": "[]",
        }
        
    async def match_batch(
        self,
        texts: list[str],
        sectors: list[str],
        sub_sectors: list[str],
        collection: str = "budget_proposed",
    ) -> list[dict]:
        """Match ALL citizen inputs in one batch embed + search."""
        if not self.store.collection_exists(collection):
            raise RuntimeError(f"Budget index '{collection}' not available.")

        queries = []
        for text, sector, sub_sector in zip(texts, sectors, sub_sectors):
            if sector and sector != "Uncategorized":
                queries.append(f"{sector}: {sub_sector}. {text}")
            else:
                queries.append(text)

        # Batch embed ALL at once
        query_vectors = self.embedder.embed_texts(queries, show_progress=False)

        results = []
        for i, qv in enumerate(query_vectors):
            vec = qv.tolist() if hasattr(qv, 'tolist') else qv
            hits = self.store.search(vec, top_k=5, collection=collection)

            if not hits or hits[0]["score"] < MATCH_THRESHOLDS["partial"]:
                results.append(self._no_match())
                continue

            best = hits[0]
            base_score = best["score"]

            if base_score >= MATCH_THRESHOLDS["matched"]:
                status, label = "matched", "Found"
            elif base_score >= MATCH_THRESHOLDS["partial"]:
                status, label = "partial", "Partial match"
            else:
                status, label = "ignored", "No match"

            excerpt = best["text"].strip()[:300]
            page = best.get("page_number", "?")
            budget_text = best.get("text", "")
            simplified = simplify_with_llm(budget_text) if settings.DEEPSEEK_API_KEY else simplify_budget_line(budget_text)

            results.append({
                "matched_line_id": best.get("chunk_id", ""),
                "matched_sector": sectors[i] if i < len(sectors) else "",
                "matched_description": best.get("text", "")[:500],
                "matched_amount_ksh": None,
                "source_page": page,
                "budget_result": f"[{label} · p.{page} · {base_score:.0%}] {excerpt}",
                "status": status,
                "similarity_score": round(base_score, 4),
                "boosted_score": round(base_score, 4),
                "simplified": simplified.get("simplified", ""),
                "key_points": simplified.get("key_points", []),
                "category": simplified.get("category", ""),
                "alternative_matches": "[]",
            })

        return results
        
    async def match_with_line_items(
        self,
        citizen_text: str,
        sector: str,
        sub_sector: str,
        ward: str | None = None,
        participation_boost: float = 0.0,
        document_id: str | None = None,
    ) -> dict:
        """Match AND look up structured line item data for actual amounts."""
        # First, do the normal semantic match
        result = await self.match(
            citizen_text, sector, sub_sector, ward,
            participation_boost, document_id,
        )
        return result  # for now, line item lookup happens in the router