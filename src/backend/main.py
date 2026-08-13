import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db.database import init_db
from .routers import submissions, wards, matches, budget, participation, classification, reports
from .dependencies import get_embedder, get_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SautiYetu API v%s", settings.APP_VERSION)
    await init_db()
    # Preload models in background
    asyncio.create_task(_preload_services())
    yield
    logger.info("Shutting down")


async def _preload_services():
    import threading
    def _load():
        get_embedder()
        get_vector_store()
        logger.info("Services preloaded")
    await asyncio.to_thread(_load)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Citizen budget accountability — Nairobi County",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(submissions.router)
app.include_router(matches.router)
app.include_router(budget.router)
app.include_router(participation.router)
app.include_router(classification.router)
app.include_router(reports.router)
app.include_router(wards.router)


@app.get("/api/health")
async def health():
    store = get_vector_store()
    ready = store.collection_exists("budget_proposed") or store.collection_exists("budget_enacted")
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "qdrant_ready": ready,
        "deepseek_configured": bool(settings.DEEPSEEK_API_KEY),
    }