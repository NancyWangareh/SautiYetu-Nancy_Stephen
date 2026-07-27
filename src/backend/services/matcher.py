import json
import openai
from .embedder import embed_text, EMBEDDING_DIM
from typing import List, Dict, Optional
from pinecone import Pinecone
from ..config import config

# Pinecone for vector search
pc = Pinecone(api_key=config.PINECONE_API_KEY)
index = pc.Index(config.PINECONE_INDEX_NAME)

# DeepSeek for reasoning about match quality
deepseek_client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

MATCH_THRESHOLDS = {
    "matched": 0.75,   # ≥ 0.75 → strong match
    "partial": 0.50,   # ≥ 0.50 → partial match
    # < 0.50 → ignored
}

async def match_citizen_to_budget(
    citizen_text: str,
    predicted_sector: str,
    predicted_sub_sector: str,
    ward: Optional[str] = None,
) -> dict:
    """
    Full matching pipeline:
    1. Embed the citizen input
    2. Query Pinecone for similar budget lines (filtered by sector)
    3. Use DeepSeek to reason about the best match from top 3
    4. Return structured match result
    
    Returns a dict ready for BudgetMatch model.
    """
    # ── Step 1: Embed ──
    try:
        query_vector = embed_text(citizen_text)
    except Exception as e:
        print(f"Embedding error: {e}")
        return _no_match_result()

    # ── Step 2: Vector search (try sector-filtered first, fallback to unfiltered) ──
    top_matches = await _vector_search(query_vector, predicted_sector, ward)

    if not top_matches:
        return _no_match_result()

    # ── Step 3: DeepSeek reasoning — pick the best match from top 3 ──
    best = await _reason_about_matches(citizen_text, top_matches, predicted_sector)

    if not best or best.get("similarity_score", 0) < MATCH_THRESHOLDS["partial"]:
        return _no_match_result(top_matches)

    # ── Step 4: Build result ──
    status = _determine_status(best["similarity_score"])

    budget_result_text = _format_budget_result(best, status)

    return {
        "matched_line_id": best.get("line_id", ""),
        "matched_sector": best.get("sector", predicted_sector),
        "matched_description": best.get("description", ""),
        "matched_amount_ksh": best.get("amount_ksh"),
        "matched_amount_requested_ksh": best.get("amount_requested_ksh"),
        "budget_result": budget_result_text,
        "status": status,
        "similarity_score": round(best["similarity_score"], 4),
        "alternative_matches": json.dumps([
            {
                "line_id": m.get("line_id"),
                "description": m.get("description", "")[:200],
                "amount_ksh": m.get("amount_ksh"),
                "score": round(m.get("similarity_score", 0), 4),
            }
            for m in top_matches[1:4]  # next 3 alternatives
        ]),
    }


async def _vector_search(
    query_vector: List[float],
    sector: str,
    ward: Optional[str] = None,
) -> List[Dict]:
    """Search Pinecone for similar budget lines."""
    filters = {}

    # Try sector-filtered first
    if sector and sector != "Uncategorized":
        filters["sector"] = {"$eq": sector}

    # If ward is known, boost ward-specific matches
    if ward:
        filters["ward"] = {"$in": [ward, "", "county-wide"]}

    try:
        results = index.query(
            vector=query_vector,
            top_k=5,
            filter=filters if filters else None,
            include_metadata=True,
        )

        matches = []
        for match in results.matches:
            matches.append({
                "id": match.id,
                "line_id": match.metadata.get("line_id", ""),
                "sector": match.metadata.get("sector", ""),
                "sub_sector": match.metadata.get("sub_sector", ""),
                "description": match.metadata.get("description", ""),
                "amount_ksh": match.metadata.get("amount_ksh", 0),
                "amount_requested_ksh": match.metadata.get("amount_requested_ksh", 0),
                "ward": match.metadata.get("ward", ""),
                "status": match.metadata.get("status", ""),
                "fiscal_year": match.metadata.get("fiscal_year", ""),
                "similarity_score": match.score,
            })
        return matches

    except Exception as e:
        print(f"Pinecone search error: {e}")
        return []


async def _reason_about_matches(
    citizen_text: str,
    top_matches: List[Dict],
    predicted_sector: str,
) -> Optional[Dict]:
    """
    Use DeepSeek to reason about which of the top 3-5 vector matches
    is the best actual match. Vector similarity is good but LLM reasoning
    catches false positives.
    """
    if not top_matches:
        return None

    # If the top match has very high similarity, skip the LLM reasoning
    if top_matches[0]["similarity_score"] >= 0.85:
        return top_matches[0]

    match_options = "\n\n".join([
        f"Option {i+1} (similarity: {m['similarity_score']:.2f}):\n"
        f"  Budget line: {m.get('line_id', '?')}\n"
        f"  Sector: {m.get('sector', '?')}\n"
        f"  Description: {m.get('description', '')}\n"
        f"  Amount: Ksh {m.get('amount_ksh', 0):,}"
        for i, m in enumerate(top_matches[:3])
    ])

    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You match Kenyan citizen budget requests to county budget lines. "
                        "Given a citizen's request and candidate budget lines with similarity scores, "
                        "pick the ONE best match. Consider: does the budget line actually address "
                        "what the citizen is asking for? A high similarity score doesn't always "
                        "mean a good match — use your judgment.\n\n"
                        "Respond ONLY with JSON: "
                        '{"best_option": 1-3, "confidence": 0.0-1.0, "reasoning": "one sentence"}'
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Citizen request: \"{citizen_text}\"\n"
                        f"Predicted sector: {predicted_sector}\n\n"
                        f"Candidate budget lines:\n{match_options}"
                    ),
                },
            ],
            temperature=0.0,
            max_tokens=250,
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]

        result = json.loads(content)
        best_idx = int(result.get("best_option", 1)) - 1

        if 0 <= best_idx < len(top_matches):
            chosen = top_matches[best_idx]
            # Blend vector similarity with LLM confidence
            chosen["llm_confidence"] = result.get("confidence", 0.5)
            chosen["llm_reasoning"] = result.get("reasoning", "")
            chosen["similarity_score"] = (
                chosen["similarity_score"] * 0.6
                + float(result.get("confidence", 0.5)) * 0.4
            )
            return chosen

    except Exception as e:
        print(f"Match reasoning error: {e}")

    # Fallback: return highest vector similarity match
    return top_matches[0]


def _determine_status(score: float) -> str:
    """Map similarity score to match status."""
    if score >= MATCH_THRESHOLDS["matched"]:
        return "matched"
    elif score >= MATCH_THRESHOLDS["partial"]:
        return "partial"
    return "ignored"


def _format_budget_result(match: Dict, status: str) -> str:
    """Format a human-readable budget result string."""
    line_id = match.get("line_id", "?")
    description = match.get("description", "budget allocation")
    amount = match.get("amount_ksh", 0)
    requested = match.get("amount_requested_ksh", amount)

    if status == "matched":
        return (
            f"Enacted Budget Line {line_id}: "
            f"Ksh {amount:,} allocated for {description.lower()}."
        )
    elif status == "partial":
        return (
            f"Enacted Budget Line {line_id}: "
            f"Ksh {amount:,} allocated of the Ksh {requested:,} requested "
            f"for {description.lower()}."
        )
    else:
        return (
            "No matching line found in the enacted budget. "
            "This request is not yet funded."
        )


def _no_match_result(alternatives: List[Dict] = None) -> dict:
    """Standard result when no match is found."""
    return {
        "matched_line_id": None,
        "matched_sector": None,
        "matched_description": None,
        "matched_amount_ksh": None,
        "matched_amount_requested_ksh": None,
        "budget_result": (
            "No matching line found in the enacted budget. "
            "This request is not yet funded."
        ),
        "status": "ignored",
        "similarity_score": 0.0,
        "alternative_matches": json.dumps(alternatives[:3] if alternatives else []),
    }