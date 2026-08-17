"""Budget matcher — semantic search against Qdrant. No fallback."""

import json
import logging
from .embedder import EmbeddingService
from .vector_store import VectorStore
from .simplifier import simplify_with_llm, simplify_budget_line
from ..config import settings
import asyncio
import openai
from .geo import normalize_location


logger = logging.getLogger(__name__)

MATCH_THRESHOLD = 0.70
VERIFY_HIGH = 0.92


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

        query = (
            f"{sector}: {sub_sector}. {citizen_text}"
            if sector and sector != "Uncategorized"
            else citizen_text
        )
        query_vector = self.embedder.embed_query(query)

        loc = normalize_location(ward)
        sector_key = sector if sector and sector != "Uncategorized" else None

        # Pass 1: constrained to the citizen's subcounty AND sector
        hits = self.store.search(
            query_vector,
            top_k=5,
            collection=collection,
            subcounty=loc["subcounty"] if loc else None,
            sector=sector_key,
        )
        relaxed_location = False
        if not hits or hits[0]["score"] < MATCH_THRESHOLD:
            # Pass 2: drop the location constraint, keep sector
            hits = self.store.search(
                query_vector, top_k=5, collection=collection, sector=sector_key
            )
            relaxed_location = True

        if not hits or hits[0]["score"] < MATCH_THRESHOLD:
            # Pass 3: drop all filters (sector/subcounty labels may not align)
            hits = self.store.search(query_vector, top_k=5, collection=collection)
            relaxed_location = True

        if not hits or hits[0]["score"] < MATCH_THRESHOLD:
            return self._no_match(reason="No relevant budget provision found.")

        best = hits[0]
        base_score = best["score"]

        # Verify with the LLM only in the uncertain band (or when location was relaxed)
        if relaxed_location or MATCH_THRESHOLD <= base_score < VERIFY_HIGH:
            verdict = await self._verify_match(citizen_text, ward, best.get("text", ""))
            if not verdict["relevant"]:
                return self._no_match(reason=verdict.get("reason", "Relevance check failed."))

        boosted_score = min(0.99, base_score + participation_boost)
        status, label = ("present", "Found") if boosted_score >= MATCH_THRESHOLD else ("absent", "No match")

        excerpt = best["text"].strip()[:300]
        page = best.get("page_number", "?")
        budget_text = best.get("text", "")
        simplified = (
            simplify_with_llm(budget_text)
            if settings.DEEPSEEK_API_KEY
            else simplify_budget_line(budget_text)
        )

        alternatives = json.dumps([
            {"text": h.get("text", "")[:200], "page": h.get("page_number"),
             "score": round(h.get("score", 0), 4)}
            for h in hits[1:4]
        ])

        return {
            "matched_line_id": best.get("chunk_id", ""),
            "matched_sector": sector,
            "matched_description": best.get("text", "")[:500],
            "matched_amount_ksh": best.get("amount_ksh"),
            "matched_location": best.get("location") or best.get("ward") or "",
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
    
    async def _verify_match(self, citizen_text: str, ward: str | None, budget_text: str) -> dict:
        """LLM gate: is this budget line actually funding THIS request (type + location)?"""
        if not settings.DEEPSEEK_API_KEY:
            return {"relevant": True, "reason": ""}

        prompt = (
            f'A citizen in ward "{ward or "unknown"}" made this request:\n'
            f'"{citizen_text[:400]}"\n\n'
            f'Candidate budget line:\n"{budget_text[:600]}"\n\n'
            "Does this budget line actually fund THIS specific request? "
            "It must match BOTH the type of work AND the location (same ward/subcounty).\n"
            'Return ONLY JSON: {"relevant": true/false, "reason": "short explanation"}'
        )

        def _call() -> str:
            client = openai.OpenAI(
                api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL
            )
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=120,
            )
            return resp.choices[0].message.content.strip()

        content = await asyncio.to_thread(_call)
        if content.startswith("```"):
            content = content.strip("`").strip()

        try:
            data = json.loads(content)
            return {"relevant": bool(data.get("relevant")), "reason": data.get("reason", "")}
        except Exception:
            logger.warning("Verification parse failed: %s", content)
            return {"relevant": True, "reason": ""}   # fail open rather than silent-drop


    def _no_match(self, reason: str = "No matching budget provision found.") -> dict:
        return {
            "matched_line_id": None,
            "matched_sector": "",
            "matched_description": reason,
            "matched_amount_ksh": None,
            "matched_location": "",
            "source_page": None,
            "budget_result": "No matching budget provision found in the budget.",
            "status": "absent",
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

            if not hits or hits[0]["score"] < MATCH_THRESHOLD:
                results.append(self._no_match())
                continue

            best = hits[0]
            base_score = best["score"]

            status, label = ("present", "Found") if base_score >= MATCH_THRESHOLD else ("absent", "No match")

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