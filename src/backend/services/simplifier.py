"""
Budget Language Simplifier — translates complex government budget lines
into plain, citizen-friendly language.
"""

import json
import logging
import re

from ..config import settings

logger = logging.getLogger(__name__)

# ── Terminology Dictionary ───────────────────────────────────────────────

TERM_DICTIONARY: dict[str, str] = {
    "programme based budget": "spending plan organized by government programmes",
    "recurrent expenditure": "day-to-day running costs (salaries, supplies, maintenance)",
    "development expenditure": "money for new projects and infrastructure",
    "capital expenditure": "money for building and long-term investments",
    "equitable share": "national government money shared equally among counties",
    "conditional grant": "national government money given for a specific purpose",
    "own source revenue": "money the county raises locally (parking fees, business permits, etc.)",
    "personal emoluments": "staff salaries and allowances",
    "operations & maintenance": "running costs (repairs, fuel, supplies)",
    "procurement": "buying goods and services",
    "construction of": "building",
    "rehabilitation of": "repairing and restoring",
    "refurbishment of": "renovating and upgrading",
    "purchase of": "buying",
    "provision for": "money set aside for",
    "completion of": "finishing the construction of",
    "expansion of": "making bigger / extending",
    "installation of": "setting up / putting in place",
    "mca": "Member of County Assembly (local elected representative)",
    "baraza": "public meeting / community gathering",
}


def translate_terms(text: str) -> str:
    """Replace complex government terminology with plain language."""
    result = text.lower()
    sorted_terms = sorted(TERM_DICTIONARY.items(), key=lambda x: len(x[0]), reverse=True)
    for term, explanation in sorted_terms:
        if " " in term or "-" in term:
            result = result.replace(term, explanation)
        else:
            result = re.sub(rf"\b{re.escape(term)}\b", explanation, result)
    return result[0].upper() + result[1:] if result else result


def simplify_budget_line(text: str) -> dict:
    """Rule-based simplification of a budget line."""
    if not text or not text.strip():
        return {"simplified": "No budget information available.", "key_points": [], "category": "unknown"}

    simplified = translate_terms(text) 
    category = _classify_spending(text.lower())

    # Extract monetary amounts
    amounts = re.findall(r"(?:KSh\.?\s*|KES\s*)?([\d,]+(?:\.\d{2})?)", simplified)

    key_points = [simplified]
    if amounts:
        key_points.append(f"The allocated amount is {amounts[0]} Kenyan Shillings.")
    key_points.append(f"This is categorized as: {category}.")

    return {"simplified": simplified, "key_points": key_points, "category": category}


def _classify_spending(text: str) -> str:
    """Classify the budget line into a spending category."""
    lower = text.lower()
    if any(w in lower for w in ["salary", "wage", "emolument", "allowance"]):
        return "salaries"
    if any(w in lower for w in ["construction", "building", "rehabilitation", "refurbishment"]):
        return "infrastructure"
    if any(w in lower for w in ["medical", "drug", "medicine", "hospital"]):
        return "health supplies"
    if any(w in lower for w in ["school", "bursary", "student", "teacher"]):
        return "education"
    if any(w in lower for w in ["maintenance", "repair"]):
        return "maintenance"
    return "general spending"


def simplify_with_llm(text: str) -> dict:
    """Use DeepSeek LLM to simplify budget text."""
    if not settings.DEEPSEEK_API_KEY:
        return simplify_budget_line(text)

    try:
        import openai
        client = openai.OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )

        prompt = f"""Translate this Kenyan county budget line into plain language that any citizen can understand.
Return ONLY JSON: {{"simplified": "...", "keyPoints": ["...", "..."], "category": "..."}}

Budget line: {text[:800]}"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=400,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        result = json.loads(content)
        return {
            "simplified": result.get("simplified", translate_terms(text)),
            "key_points": result.get("keyPoints", result.get("key_points", [])),
            "category": result.get("category", "unknown"),
        }

    except Exception as e:
        logger.warning("LLM simplification failed: %s. Using rules.", e)
        return simplify_budget_line(text)