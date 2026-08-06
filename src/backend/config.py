import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── DeepSeek (for classification & translation only; NOT for structuring) ──
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    # ── Qdrant (local file-based vector DB — fast & free) ──
    QDRANT_PATH = Path(__file__).resolve().parents[2] / "data" / "qdrant_storage"

    # ── Supabase (structured database for submissions & matches) ──
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

    # ── File size limit ──
    MAX_PDF_SIZE_MB = int(os.getenv("MAX_PDF_SIZE_MB", "50"))

    # ── Budget sectors ──
    BUDGET_SECTORS = [
        "Health", "Education", "Infrastructure", "Water & Sanitation",
        "Agriculture", "Energy", "Security", "Governance", "Trade",
        "Environment", "Social Protection", "Uncategorized"
    ]

config = Config()