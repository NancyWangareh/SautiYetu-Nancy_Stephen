from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # ── App ──
    APP_NAME: str = "SautiYetu API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # ── Database ──
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/sautiyetu.db"

    # ── DeepSeek / LLM ──
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"

    # ── Embedding ──
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-small"
    EMBEDDING_DEVICE: str = "cpu"

    # ── Qdrant ──
    QDRANT_PATH: str = str(Path(__file__).resolve().parents[2] / "data" / "qdrant_storage")
    QDRANT_URL: str = ""

    # ── CORS ──
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:5174"]

    # ── PDF ──
    MAX_PDF_SIZE_MB: int = 50
    DEFAULT_BUDGET_PDF: str = ""

    model_config = {
        "env_file": str(Path(__file__).resolve().parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()