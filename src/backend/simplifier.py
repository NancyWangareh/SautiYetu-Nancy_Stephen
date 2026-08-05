"""
Budget Language Simplifier — translates complex government budget lines
into plain, citizen-friendly language that anyone can understand.

Handles common Kenyan government budget terminology, accounting codes,
and bureaucratic phrasing found in Nairobi County budget documents.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ── Terminology Dictionary ───────────────────────────────────────────────
# Maps complex government terms → plain language explanations

TERM_DICTIONARY: dict[str, str] = {
    # === Budget Document Structure ===
    "programme based budget": "spending plan organized by government programmes",
    "program based budget": "spending plan organized by government programmes",
    "recurrent expenditure": "day-to-day running costs (salaries, supplies, maintenance)",
    "recurrent estimates": "projected day-to-day running costs",
    "development expenditure": "money for new projects and infrastructure",
    "development estimates": "projected spending on new projects and infrastructure",
    "capital expenditure": "money for building and long-term investments",
    "supplementary estimates": "revised/additional budget after the main budget was passed",
    "supplementary ii": "second round of budget revisions for the year",
    "appropriation in aid": "money the county expects to collect on its own (e.g., fees, levies)",
    "appropriations in aid": "money the county expects to collect on its own (e.g., fees, levies)",
    "gross estimates": "total projected cost before deducting any income",
    "net estimates": "cost after deducting expected income",

    # === Accounting Codes & Classifications ===
    "vote": "department or ministry budget",
    "sub-vote": "division within a department's budget",
    "head": "budget category",
    "sub-head": "sub-category of spending",
    "item": "specific budget line item",
    "gfs code": "government financial classification code",
    "gfs": "government financial classification code",
    "economic classification": "what the money is spent on (salaries, goods, assets)",

    # === Funding Classifications ===
    "equitable share": "national government money shared equally among counties",
    "conditional grant": "national government money given for a specific purpose",
    "conditional allocation": "national government money given for a specific purpose",
    "own source revenue": "money the county raises locally (parking fees, business permits, etc.)",
    "osr": "money the county raises locally (parking fees, business permits, etc.)",
    "exchequer": "the national treasury",
    "consolidated fund": "the main government bank account",
    "county revenue fund": "the county's main bank account",

    # === Personnel & Staffing ===
    "personal emoluments": "staff salaries and allowances",
    "basic salary": "base pay before allowances",
    "house allowance": "housing benefit paid to staff",
    "commuter allowance": "transport allowance paid to staff",
    "leave allowance": "annual leave pay",
    "medical allowance": "healthcare benefit for staff",
    "casual labour": "temporary/daily wage workers",
    "permanent & pensionable": "permanent employees with retirement benefits",
    "contractual employees": "staff hired on fixed-term contracts",
    "nhif": "National Hospital Insurance Fund contributions",
    "nssf": "National Social Security Fund contributions",

    # === Operations & Maintenance ===
    "operations & maintenance": "running costs (repairs, fuel, supplies)",
    "o & m": "running costs (repairs, fuel, supplies)",
    "o&m": "running costs (repairs, fuel, supplies)",
    "utilities": "electricity, water, and phone bills",
    "routine maintenance": "regular upkeep and repairs",
    "refurbishment": "renovation and upgrade of buildings/facilities",
    "rehabilitation": "repairing and restoring old infrastructure",
    "capacity building": "training and skills development for staff",

    # === Procurement & Assets ===
    "procurement": "buying goods and services",
    "purchase of goods & services": "buying supplies and services",
    "acquisition of assets": "buying equipment, vehicles, or buildings",
    "plant & machinery": "heavy equipment and machines",
    "motor vehicles": "cars, trucks, and transport vehicles",
    "office furniture & equipment": "desks, chairs, computers, and office tools",
    "ict equipment": "computers, printers, and technology equipment",
    "ict infrastructure": "technology systems and networks",

    # === Common Budget Line Patterns ===
    "printing & stationery": "printing documents and office supplies (paper, pens, etc.)",
    "hospitality": "refreshments and meals for meetings",
    "travel & subsistence": "transport and meal costs for official trips",
    "domestic travel": "travel within the country for work",
    "foreign travel": "international work trips",
    "training expenses": "costs for staff training and workshops",
    "board & committee expenses": "sitting allowances and costs for committee meetings",

    # === Sector-Specific Terms ===
    "medical supplies": "medicines, syringes, bandages, and hospital supplies",
    "non-pharmaceutical supplies": "non-drug hospital items (gloves, gowns, etc.)",
    "pharmaceutical supplies": "medicines and drugs",
    "laboratory supplies": "test tubes, reagents, and lab equipment consumables",
    "drugs & dressings": "medicines and wound care supplies",
    "therapeutic diets": "special meals for patients who need them",
    "mortuary services": "morgue and body preservation services",
    "ambulance services": "emergency medical transport",
    "health infrastructure": "hospital and clinic buildings",
    "maternal & child health": "services for pregnant women and young children",
    "immunization programme": "vaccination drives for children and adults",
    "school feeding programme": "meals provided to school children",
    "bursary fund": "scholarships and school fee assistance",
    "ecd infrastructure": "early childhood development centre buildings",
    "tertiary institutions": "colleges, polytechnics, and universities",
    "road gravelling": "adding gravel to unpaved roads",
    "road grading": "levelling and smoothing dirt/gravel roads",
    "stormwater drainage": "drains and channels for rainwater runoff",
    "street lighting": "lamp posts and lights along roads",
    "solid waste management": "garbage collection and disposal",
    "water reticulation": "water pipe networks to supply homes",
    "borehole drilling": "drilling deep wells for water",
    "sewerage system": "sewage and wastewater pipes and treatment",
    "cattle dip": "livestock treatment facility to kill parasites",
    "veterinary services": "animal healthcare services",
    "agricultural extension": "farmers' training and advisory services",
    "crop diversification": "growing different types of crops",
    "market infrastructure": "market stalls, sheds, and trading spaces",
    "feeder roads": "small roads connecting villages to main roads",

    # === Budget Actions ===
    "construction of": "building",
    "rehabilitation of": "repairing and restoring",
    "refurbishment of": "renovating and upgrading",
    "purchase of": "buying",
    "provision for": "money set aside for",
    "completion of": "finishing the construction of",
    "expansion of": "making bigger / extending",
    "installation of": "setting up / putting in place",
    "operationalization of": "making operational / getting it running",

    # === Kenyan-Specific Terms ===
    "mca": "Member of County Assembly (local elected representative)",
    "mcas": "Members of County Assembly (local elected representatives)",
    "ward administrator": "local government official in charge of a ward",
    "sub-county": "area within a county (smaller than constituency)",
    "baraza": "public meeting / community gathering",
    "nyumba kumi": "community policing initiative (10 households)",
    "polytechnic": "technical/vocational training college",
    "vtc": "village technical/vocational training centre",
    "murram": "gravel material used on rural roads",
    "cabro": "concrete paving blocks used for roads and walkways",
}


def translate_terms(text: str) -> str:
    """
    Replace complex government terminology with plain language explanations.

    Uses the TERM_DICTIONARY to substitute jargon with simple explanations.
    Longer phrases are matched first to avoid partial-match issues.
    """
    result = text.lower()

    # Sort by phrase length (longest first) to avoid partial replacements
    sorted_terms = sorted(TERM_DICTIONARY.items(), key=lambda x: len(x[0]), reverse=True)

    for term, explanation in sorted_terms:
        pattern = re.escape(term)
        # Only replace whole word/phrase boundaries
        # Use word boundaries for single words, simpler matching for phrases
        if " " in term or "-" in term:
            result = result.replace(term, explanation)
        else:
            result = re.sub(
                rf"\b{pattern}\b",
                explanation,
                result,
            )

    # Capitalize first letter
    result = result[0].upper() + result[1:] if result else result

    return result


# ── Amount / Number Simplifier ───────────────────────────────────────────

def simplify_amount(amount_str: str) -> str:
    """
    Convert budget amounts into human-readable text.
    E.g., "12,345,678" → "about 12.3 million shillings"
          "987,654" → "about 988 thousand shillings"
    """
    # Remove commas, spaces, and "KSh"/"KES" prefixes
    cleaned = re.sub(r"[,\s]|(?i)ksh|kes|sh\.?\s*", "", amount_str)

    try:
        value = float(cleaned)
    except ValueError:
        return amount_str

    if value >= 1_000_000_000:
        billions = value / 1_000_000_000
        return f"about {billions:.1f} billion shillings"
    elif value >= 1_000_000:
        millions = value / 1_000_000
        return f"about {millions:.1f} million shillings"
    elif value >= 1_000:
        thousands = value / 1_000
        return f"about {thousands:,.0f} thousand shillings"
    else:
        return f"{value:,.0f} shillings"


# ── Budget Line Simplifier ───────────────────────────────────────────────

def simplify_budget_line(text: str) -> dict:
    """
    Take a raw budget line from the PDF and produce a citizen-friendly explanation.

    Returns a dict with:
        - original: the original text
        - simplified: plain-language version
        - keyPoints: a list of 2-4 bullet points in simple language
        - category: what kind of spending this is (salaries, projects, supplies, etc.)
    """
    if not text or not text.strip():
        return {
            "original": text,
            "simplified": "No budget information available.",
            "keyPoints": [],
            "category": "unknown",
        }

    original = text.strip()

    # Step 1: Translate terminology
    simplified = translate_terms(original)

    # Step 2: Extract and simplify monetary amounts
    amount_pattern = r"(?:KSh\.?\s*|KES\s*|Sh\.?\s*)?([\d,]+(?:\.\d{2})?)"
    amounts = re.findall(amount_pattern, simplified)

    # Step 3: Determine spending category
    category = _classify_spending(original.lower())

    # Step 4: Generate key points
    key_points = _generate_key_points(original, category)

    return {
        "original": original,
        "simplified": simplified,
        "keyPoints": key_points,
        "category": category,
    }


def _classify_spending(text: str) -> str:
    """Classify the budget line into a high-level spending category."""
    lower = text.lower()

    if any(w in lower for w in ["salary", "wage", "emolument", "allowance", "casual labour"]):
        return "salaries"
    if any(w in lower for w in ["construction", "rehabilitation", "refurbishment", "building"]):
        return "infrastructure"
    if any(w in lower for w in ["medical", "drug", "medicine", "pharmaceutical", "hospital supplies"]):
        return "medical supplies & drugs"
    if any(w in lower for w in ["training", "capacity building", "workshop", "seminar"]):
        return "training & capacity building"
    if any(w in lower for w in ["vehicle", "motor", "car", "truck", "ambulance"]):
        return "vehicles & transport"
    if any(w in lower for w in ["equipment", "furniture", "computer", "ict", "printer"]):
        return "equipment & furniture"
    if any(w in lower for w in ["food", "feeding", "meal", "diet", "nutrition"]):
        return "food & nutrition"
    if any(w in lower for w in ["water", "borehole", "sewer", "sanitation", "toilet"]):
        return "water & sanitation"
    if any(w in lower for w in ["road", "drain", "street", "bridge", "footpath"]):
        return "roads & transport"
    if any(w in lower for w in ["electric", "power", "solar", "lighting", "transformer"]):
        return "energy & electricity"
    if any(w in lower for w in ["education", "school", "bursary", "library", "classroom"]):
        return "education"
    if any(w in lower for w in ["agriculture", "farm", "livestock", "crop", "veterinary"]):
        return "agriculture"
    if any(w in lower for w in ["security", "police", "safety", "crime"]):
        return "security"

    return "general spending"


def _generate_key_points(text: str, category: str) -> list[str]:
    """
    Generate 2-4 plain-language bullet points explaining what this budget line means
    for a regular citizen.
    """
    points: list[str] = []
    lower = text.lower()

    # Category-specific explanations
    category_explanations = {
        "salaries": [
            "This is money used to pay staff salaries and allowances.",
            "Salaries are recurring costs — they are paid every year.",
        ],
        "infrastructure": [
            "This is money for building or repairing physical structures like buildings, roads, or water systems.",
            "Once built, this infrastructure benefits the community for many years.",
        ],
        "medical supplies & drugs": [
            "This is money for medicines, hospital supplies, and medical equipment.",
            "These supplies directly affect the quality of healthcare you receive at local clinics and hospitals.",
        ],
        "training & capacity building": [
            "This is money used to train government staff or community members.",
            "Training helps improve the quality of services delivered to citizens.",
        ],
        "vehicles & transport": [
            "This is money for buying or maintaining vehicles like ambulances, trucks, or official cars.",
        ],
        "equipment & furniture": [
            "This is money for buying office equipment, computers, furniture, and tools.",
        ],
        "food & nutrition": [
            "This is money for food programmes, such as school feeding or hospital patient meals.",
        ],
        "water & sanitation": [
            "This is money for water supply, boreholes, toilets, and sewage systems.",
            "Access to clean water and sanitation directly improves community health.",
        ],
        "roads & transport": [
            "This is money for building, repairing, or maintaining roads, footpaths, and drainage systems.",
            "Good roads improve access to markets, schools, and hospitals.",
        ],
        "energy & electricity": [
            "This is money for electricity connections, street lights, and solar power installations.",
        ],
        "education": [
            "This is money for schools, bursaries, libraries, or classroom construction.",
            "Education spending affects the quality of learning for children in your community.",
        ],
        "agriculture": [
            "This is money for farming support, livestock health, or agricultural extension services.",
        ],
        "security": [
            "This is money for community safety, policing, and crime prevention.",
        ],
    }

    # Add category explanation
    explanations = category_explanations.get(category, ["This is part of the government's spending plan for the year."])
    points.extend(explanations)

    # Add specific observations from the text
    if "million" in lower or "billion" in lower or "thousand" in lower:
        # Find the money amount
        amounts = re.findall(r"(?:ksh\.?\s*|kes\s*|sh\.?\s*)?([\d,]+(?:\.\d{2})?)", lower)
        if amounts:
            human_amount = simplify_amount(amounts[0])
            points.append(f"The amount allocated is {human_amount}.")

    if "construction" in lower or "building" in lower or "rehabilitation" in lower:
        points.append("This is a one-time project cost (not a recurring expense).")
    elif "salary" in lower or "wage" in lower or "emolument" in lower:
        points.append("This is a recurring cost that is budgeted every financial year.")

    # Add a citizen impact statement
    impact = _get_citizen_impact(category)
    if impact:
        points.append(impact)

    return points[:4]  # Limit to 4 key points


def _get_citizen_impact(category: str) -> str | None:
    """Return a citizen-focused impact statement for the spending category."""
    impacts = {
        "salaries": "When salaries are funded, frontline workers like nurses, teachers, and clerks can be paid on time.",
        "infrastructure": "This infrastructure project creates jobs during construction and delivers lasting benefits to the community.",
        "medical supplies & drugs": "When medical supplies are funded, your local clinic or hospital has the medicines you need.",
        "training & capacity building": "Well-trained staff provide better services to you and your community.",
        "vehicles & transport": "This helps ensure government services can reach your area.",
        "equipment & furniture": "Proper equipment enables government offices to serve you more efficiently.",
        "food & nutrition": "Nutrition programmes help keep children healthy and able to learn at school.",
        "water & sanitation": "Clean water and sanitation prevent disease and improve quality of life in communities.",
        "roads & transport": "Good roads mean faster travel, lower transport costs, and better access to essential services.",
        "energy & electricity": "Electricity and street lighting improve safety, enable businesses, and help children study at night.",
        "education": "Education spending shapes the future of our children and builds a skilled workforce.",
        "agriculture": "Agricultural support helps farmers grow more food, improving food security and household incomes.",
        "security": "Safety and security are fundamental to community well-being and economic activity.",
    }
    return impacts.get(category)


# ── LLM-based Simplifier (Optional) ──────────────────────────────────────

def simplify_with_llm(text: str) -> dict:
    """
    Use an LLM (via environment-configured API) to produce an even better
    plain-language explanation of a budget line.

    Checks in order:
        - DEEPSEEK_API_KEY env var set (uses deepseek-chat)
        - OPENAI_API_KEY env var set (uses gpt-4o-mini)
        - OLLAMA_HOST env var set (uses local Ollama with llama3.2)

    Falls back to rule-based simplifier if no LLM is available.
    """
    import os

    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    ollama_host = os.environ.get("OLLAMA_HOST", "")

    if deepseek_key:
        return _simplify_with_deepseek(text, deepseek_key)
    elif openai_key:
        return _simplify_with_openai(text, openai_key)
    elif ollama_host:
        return _simplify_with_ollama(text, ollama_host)
    else:
        logger.info("No LLM configured — using rule-based simplifier")
        return simplify_budget_line(text)


def _simplify_with_deepseek(text: str, api_key: str) -> dict:
    """Use DeepSeek API (OpenAI-compatible) to simplify budget text."""
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

        prompt = f"""You are a translator who converts Kenyan government budget lines into plain language for citizens.

CRITICAL RULES — follow strictly to avoid misinformation:
1. ONLY use information explicitly present in the budget text. Do NOT add, infer, guess, or embellish anything.
2. Preserve ALL specific numbers, amounts, figures, and ward/location names exactly as they appear in the source.
3. If the text is unclear or ambiguous, say so rather than guessing.
4. Every claim in your output MUST be traceable back to the source text below.

Return a JSON object with:
- "simplified": A 2-4 sentence plain-language explanation using ONLY facts from the text
- "keyPoints": An array of 2-4 bullet points, each verifiable against the source text
- "category": One of: "salaries", "infrastructure", "medical supplies & drugs", "training & capacity building", "vehicles & transport", "equipment & furniture", "food & nutrition", "water & sanitation", "roads & transport", "energy & electricity", "education", "agriculture", "security", "general spending"

Budget line to explain:
{text}

Respond with ONLY valid JSON, no other text."""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )

        content = response.choices[0].message.content or "{}"
        result = __import__("json").loads(content)
        result["original"] = text
        
        # Post-validation: check that key numbers from source appear in simplified output
        import re as _re
        src_numbers = set(_re.findall(r'[\d,]{4,}', text))
        simplified_text = result.get("simplified", "")
        sim_numbers = set(_re.findall(r'[\d,]{4,}', simplified_text))
        if src_numbers and not (src_numbers & sim_numbers):
            logger.warning("DeepSeek may have dropped budget figures — falling back to rule-based")
            return simplify_budget_line(text)
        
        return result

    except Exception as e:
        logger.warning("DeepSeek simplification failed: %s — falling back to rule-based", e)
        return simplify_budget_line(text)


def _simplify_with_openai(text: str, api_key: str) -> dict:
    """Use OpenAI API to simplify budget text."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        prompt = f"""You are a translator who converts Kenyan government budget lines into plain language for citizens.

CRITICAL RULES — follow strictly to avoid misinformation:
1. ONLY use information explicitly present in the budget text. Do NOT add, infer, guess, or embellish anything.
2. Preserve ALL specific numbers, amounts, figures, and ward/location names exactly as they appear in the source.
3. If the text is unclear or ambiguous, say so rather than guessing.
4. Every claim in your output MUST be traceable back to the source text below.

Return a JSON object with:
- "simplified": A 2-4 sentence plain-language explanation using ONLY facts from the text
- "keyPoints": An array of 2-4 bullet points, each verifiable against the source text
- "category": One of: "salaries", "infrastructure", "medical supplies & drugs", "training & capacity building", "vehicles & transport", "equipment & furniture", "food & nutrition", "water & sanitation", "roads & transport", "energy & electricity", "education", "agriculture", "security", "general spending"

Budget line to explain:
{text}

Respond with ONLY valid JSON, no other text."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )

        content = response.choices[0].message.content or "{}"
        result = __import__("json").loads(content)
        result["original"] = text
        return result

    except Exception as e:
        logger.warning("OpenAI simplification failed: %s — falling back to rule-based", e)
        return simplify_budget_line(text)


def _simplify_with_ollama(text: str, host: str) -> dict:
    """Use local Ollama instance to simplify budget text."""
    import json as _json

    try:
        import urllib.request

        prompt = f"""You are a helpful translator who explains Kenyan government budget documents to ordinary citizens. 

Take this budget line from a Nairobi County budget document and explain it in plain, simple language. Return ONLY a JSON object (no other text) with these fields:
- "simplified": 2-4 sentence explanation in very simple English
- "keyPoints": array of 2-4 bullet points
- "category": one of ["salaries","infrastructure","medical supplies & drugs","training & capacity building","vehicles & transport","equipment & furniture","food & nutrition","water & sanitation","roads & transport","energy & electricity","education","agriculture","security","general spending"]

Budget line: {text}

JSON response:"""

        data = _json.dumps({
            "model": "llama3.2",
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{host.rstrip('/')}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())

        content = result.get("response", "{}")
        parsed = _json.loads(content)
        parsed["original"] = text
        return parsed

    except Exception as e:
        logger.warning("Ollama simplification failed: %s — falling back to rule-based", e)
        return simplify_budget_line(text)


# ── Convenience: Process multiple budget lines ───────────────────────────

def simplify_budget_lines(texts: list[str], use_llm: bool = False) -> list[dict]:
    """
    Simplify multiple budget lines at once.

    Args:
        texts: List of raw budget line texts
        use_llm: If True, attempt LLM-based simplification (falls back to rule-based)

    Returns:
        List of dicts with original, simplified, keyPoints, and category
    """
    if use_llm:
        return [simplify_with_llm(t) for t in texts]
    return [simplify_budget_line(t) for t in texts]
