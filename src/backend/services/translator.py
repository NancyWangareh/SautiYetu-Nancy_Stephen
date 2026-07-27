import openai
from ..config import config

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

# Common Sheng/Swahili words that indicate non-English input
SHENG_MARKERS = [
    "tunahitaji", "tunaomba", "saidia", "tafadhali", "jamani",
    "kijiji", "kata", "watu", "wananchi", "serikali", "kaunti",
    "ng'ombe", "mahindi", "shamba", "maji", "barabara", "shule",
    "afya", "usalama", "umeme", "takataka", "soko",
    "iko", "haina", "mbaya", "sana", "kabisa", "bado",
    "nataka", "wanataka", "imeharibika", "tumesahauliwa",
]


def needs_translation(text: str) -> bool:
    """Heuristic: check if text contains significant Swahili/Sheng."""
    words = text.lower().split()
    if not words:
        return False
    sheng_count = sum(1 for w in words if w in SHENG_MARKERS)
    return sheng_count >= 2  # At least 2 Sheng markers


async def translate_to_english(text: str) -> dict:
    """
    Translate Sheng/Swahili text to English using DeepSeek.
    Returns {translated_text, original_language, was_translated}.
    """
    if not needs_translation(text):
        return {
            "translated_text": text,
            "original_language": "en",
            "was_translated": False,
        }

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a Kenyan language translator. "
                        "Translate the following text from Swahili or Sheng into clear English. "
                        "Preserve the original meaning, emotion, and specific place names. "
                        "Keep Kenyan locations and terms (like 'baraza', 'murram', 'boda boda') as-is. "
                        "Respond with ONLY the translated English text. No explanation."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            max_tokens=500,
        )

        translated = response.choices[0].message.content.strip()
        return {
            "translated_text": translated,
            "original_language": "sw",
            "was_translated": True,
        }

    except Exception as e:
        print(f"Translation error: {e}")
        return {
            "translated_text": text,
            "original_language": "unknown",
            "was_translated": False,
        }