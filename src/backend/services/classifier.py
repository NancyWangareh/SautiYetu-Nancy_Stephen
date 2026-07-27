import json
import openai
from typing import Optional
from ..config import config

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

CLASSIFICATION_PROMPT = """You are a Kenyan county budget classifier for Nairobi City County.
Classify citizen requests into a sector and sub-sector.

AVAILABLE SECTORS AND SUB-SECTORS:
- Health: Maternal Care, Service Delivery, NHIF, Health Infrastructure
- Education: Early Childhood Development, Schools & Learning, Bursaries & Scholarships, Tertiary
- Infrastructure: Roads & Transport, Public Works, Housing & Urban Development, Drainage
- Water & Sanitation: Water Supply, Sewerage, Sanitation & Toilets, Garbage Collection
- Agriculture: Livestock Health, Crop Farming, Fisheries, Veterinary Services
- Energy: Rural Electrification, Street Lighting, Solar Power
- Security: Community Safety, Policing, Fire Services, Disaster Management
- Governance: Administration, ICT, Civic Education, Public Participation
- Trade: Markets, Trade Licenses, Cooperatives
- Environment: Waste Management, Parks & Green Spaces, Tree Planting
- Social Protection: Youth Programs, Women Empowerment, PWD Support, Elderly Support
- Uncategorized: if genuinely unclear

RULES:
1. If the text mentions a specific facility (dispensary, school, road, market), use that to infer the sector.
2. If the text is in Swahili or Sheng, still classify based on meaning.
3. Confidence should reflect how clearly the text maps to one sector.
4. Be specific with sub-sectors — "dispensary" → "Service Delivery", not just "Health".

Respond ONLY with a JSON object. No markdown, no explanation:
{"sector": "...", "sub_sector": "...", "confidence": 0.0-1.0, "reasoning": "one short sentence"}"""


async def classify_citizen_input(text: str) -> dict:
    """
    Use DeepSeek to classify a citizen's budget request into sector/sub-sector.
    Returns {sector, sub_sector, confidence, reasoning}.
    """
    if not text or len(text.strip()) < 5:
        return {
            "sector": "Uncategorized",
            "sub_sector": "Needs Review",
            "confidence": 0.0,
            "reasoning": "Input too short to classify",
        }

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": CLASSIFICATION_PROMPT},
                {"role": "user", "content": text.strip()},
            ],
            temperature=0.0,
            max_tokens=300,
        )

        content = response.choices[0].message.content.strip()
        # Strip markdown fences if present
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
            "reasoning": result.get("reasoning", ""),
        }

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Classification parse error: {e}. Raw: {content[:200] if 'content' in dir() else 'N/A'}")
        return {
            "sector": "Uncategorized",
            "sub_sector": "Needs Review",
            "confidence": 0.0,
            "reasoning": "Classification failed — needs manual review",
        }
    except Exception as e:
        print(f"Classification API error: {e}")
        return {
            "sector": "Uncategorized",
            "sub_sector": "Needs Review",
            "confidence": 0.0,
            "reasoning": f"API error: {str(e)[:100]}",
        }