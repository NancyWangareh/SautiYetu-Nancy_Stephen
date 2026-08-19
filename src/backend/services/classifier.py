"""DeepSeek classifier — no keyword fallback. If API fails, it fails."""

import json
import logging
import openai
from ..config import settings
import re

logger = logging.getLogger(__name__)

SECTORS = [
    "Health", "Education", "Infrastructure", "Water & Sanitation",
    "Agriculture", "Energy", "Security", "Governance", "Trade",
    "Environment", "Social Protection", "Uncategorized",
]

BUDGET_LINE_PROMPT = """You classify Kenyan county budget line items (projects).

Use ONLY this sector taxonomy: """ + ", ".join(SECTORS) + """.

For each line, pick the sector and a sub-sector (e.g. Roads & Transport, Sewerage,
Water Supply, Public Works, Markets, Street Lighting, Waste Management, etc.).

Return ONLY a JSON array with one object per line, in the same order:
[{"sector":"...","sub_sector":"...","confidence":0.0-1.0}, ...]"""

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
- Uncategorized: if truly unclear (use sparingly)

Return ONLY valid JSON: {"sector":"...","sub_sector":"...","confidence":0.0-1.0}"""


class ClassifierService:
    def __init__(self, embedder=None):
        self.embedder = embedder
        self.client = openai.OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        ) if settings.DEEPSEEK_API_KEY else None

    async def classify(self, text: str) -> dict:
        if not self.client:
            raise RuntimeError("DEEPSEEK_API_KEY not configured. Classification unavailable.")

        if len(text.strip()) < 5:
            raise ValueError("Input too short for classification.")

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": CLASSIFICATION_PROMPT},
                    {"role": "user", "content": text.strip()},
                ],
                temperature=0.0,
                max_tokens=200,
            )
            content = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
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

        except json.JSONDecodeError:
            logger.error("DeepSeek returned non-JSON: %s", content)
            raise RuntimeError("Classification failed: invalid response format.")
        except Exception as e:
            logger.error("Classification failed: %s", e)
            raise RuntimeError(f"Classification failed: {str(e)[:200]}")
        
    async def classify_batch(self, texts: list[str]) -> list[dict]:
        if not self.client:
            raise RuntimeError("DEEPSEEK_API_KEY not configured.")

        numbered = "\n".join(
            f"{i+1}. {t.strip()[:200]}" for i, t in enumerate(texts) if t.strip()
        )

        prompt = f"""Classify each into a sector and sub-sector. Return ONLY a JSON array.

{numbered}

SECTORS: Health, Education, Infrastructure, Water & Sanitation, Agriculture, Energy, Security, Governance, Trade, Environment, Social Protection, Uncategorized

Return ONLY: [{{"sector":"...", "sub_sector":"...", "confidence":0.0-1.0}}, ...]"""

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=4000,
            )
            content = response.choices[0].message.content.strip()

            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            try:
                results = json.loads(content)
            except json.JSONDecodeError:
                content = content.replace("\n", " ")
                try:
                    results = json.loads(content)
                except json.JSONDecodeError:
                    import re
                    results = []
                    for m in re.finditer(r'\{[^{}]*\}', content):
                        try:
                            results.append(json.loads(m.group()))
                        except json.JSONDecodeError:
                            pass

            if not isinstance(results, list):
                raise ValueError("Not a list")

            while len(results) < len(texts):
                results.append({"sector": "Uncategorized", "sub_sector": "Needs Review", "confidence": 0.0})

            return results[:len(texts)]

        except Exception as e:
            logger.error("Batch classification failed: %s", e)
            raise RuntimeError(f"Batch classification failed: {str(e)[:200]}")
        
    async def classify_budget_lines(self, lines: list[str]) -> list[dict]:
        """Batch-classify budget line items in small chunks for reliable ordering."""
        if not self.client:
            raise RuntimeError("DEEPSEEK_API_KEY not configured.")

        import asyncio

        BATCH_SIZE = 40
        all_results: list[dict] = []

        for start in range(0, len(lines), BATCH_SIZE):
            batch = lines[start:start + BATCH_SIZE]
            numbered = "\n".join(
                f"{i+1}. {t.strip()[:200]}" for i, t in enumerate(batch) if t.strip()
            )
            prompt = f"{BUDGET_LINE_PROMPT}\n\n{numbered}"

            def _call(p: str = prompt, retries: int = 2) -> str:
                last_exc = None
                for attempt in range(retries + 1):
                    try:
                        resp = self.client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role": "user", "content": p}],
                            temperature=0.0,
                            max_tokens=4000,
                        )
                        return resp.choices[0].message.content.strip()
                    except Exception as e:
                        last_exc = e
                        if attempt < retries:
                            import time
                            time.sleep(2 * (attempt + 1))
                raise last_exc

            content = await asyncio.to_thread(_call)

            if content.startswith("```"):
                content = content.strip("`").strip()

            try:
                results = json.loads(content)
            except json.JSONDecodeError:
                results = []
                for m in re.finditer(r"\{[^{}]*\}", content):
                    try:
                        results.append(json.loads(m.group()))
                    except json.JSONDecodeError:
                        pass

            if not isinstance(results, list):
                results = []

            while len(results) < len(batch):
                results.append({"sector": "Uncategorized", "sub_sector": "", "confidence": 0.0})
            results = results[:len(batch)]

            all_results.extend(results)

        return all_results