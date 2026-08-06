"""
Lightweight classifier — DeepSeek for accurate classification,
fallback to keyword rules if API is unavailable.
"""
import json
import logging
from typing import Optional

import openai
from ..config import config

logger = logging.getLogger(__name__)

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

CLASSIFICATION_PROMPT = """You are a Kenyan county budget classifier.
Classify this citizen request into a sector and sub-sector.

SECTORS:
- Health: Maternal Care, Service Delivery, NHIF, Health Infrastructure
- Education: ECD, Schools & Learning, Bursaries, Tertiary
- Infrastructure: Roads & Transport, Public Works, Housing, Drainage
- Water & Sanitation: Water Supply, Sewerage, Sanitation, Garbage
- Agriculture: Livestock, Crop Farming, Fisheries, Veterinary
- Energy: Rural Electrification, Street Lighting, Solar
- Security: Community Safety, Policing, Fire Services
- Governance: Administration, ICT, Civic Education
- Trade: Markets, Trade Licenses, Cooperatives
- Environment: Waste Management, Parks, Tree Planting
- Social Protection: Youth, Women, PWD, Elderly
- Uncategorized: if unclear

Return ONLY JSON: {"sector":"...","sub_sector":"...","confidence":0.0-1.0}"""


async def classify_citizen_input(text: str) -> dict:
    """Classify citizen input. Falls back to keywords if API fails."""
    if not text or len(text.strip()) < 5:
        return {"sector": "Uncategorized", "sub_sector": "Needs Review", "confidence": 0.0}

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": CLASSIFICATION_PROMPT},
                {"role": "user", "content": text.strip()},
            ],
            temperature=0.0,
            max_tokens=200,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        result = json.loads(content)
        return {
            "sector": result.get("sector", "Uncategorized"),
            "sub_sector": result.get("sub_sector", "Needs Review"),
            "confidence": float(result.get("confidence", 0.0)),
        }

    except Exception as e:
        logger.warning("Classification API failed: %s. Using fallback.", e)
        return _fallback(text)


def _fallback(text: str) -> dict:
    """Keyword-based fallback classification."""
    t = text.lower()
    mapping = [
        (("health", "clinic", "dispensary", "maternity", "nhif", "hospital"), ("Health", "Service Delivery")),
        (("school", "teacher", "student", "learning", "ecd", "bursar"), ("Education", "Schools & Learning")),
        (("road", "transport", "bridge", "pothole", "drain"), ("Infrastructure", "Roads & Transport")),
        (("water", "tap", "pipe", "sewer", "sanitation"), ("Water & Sanitation", "Water Supply")),
        (("security", "police", "safety", "crime", "patrol"), ("Security", "Community Safety")),
        (("market", "vendor", "trading", "commerce"), ("Trade", "Markets")),
        (("waste", "garbage", "clean", "tree", "environment"), ("Environment", "Waste Management")),
        (("youth", "women", "pwd", "elderly", "social"), ("Social Protection", "Youth Programs")),
        (("electric", "lighting", "solar", "power"), ("Energy", "Rural Electrification")),
        (("farm", "crop", "livestock", "fish"), ("Agriculture", "Crop Farming")),
        (("ict", "governance", "admin", "civic"), ("Governance", "Administration")),
    ]
    for keywords, (sector, sub) in mapping:
        if any(k in t for k in keywords):
            return {"sector": sector, "sub_sector": sub, "confidence": 0.6}
    return {"sector": "Uncategorized", "sub_sector": "Needs Review", "confidence": 0.0}