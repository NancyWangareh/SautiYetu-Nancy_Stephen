from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db.database import init_db
from .routers import budget, submissions, matches


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables. Shutdown: clean up."""
    await init_db()
    yield


app = FastAPI(
    title="SautiYetu API",
    description="Citizen budget accountability — Nairobi County",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(budget.router)
app.include_router(submissions.router)
app.include_router(matches.router)


@app.get("/")
async def root():
    return {
        "service": "SautiYetu API",
        "endpoints": {
            "classify": "POST /api/submissions/classify",
            "submit": "POST /api/submissions",
            "list_submissions": "GET /api/submissions",
            "list_matches": "GET /api/matches",
            "match_stats": "GET /api/matches/stats",
            "rematch": "POST /api/matches/rematch/{id}",
            "upload_budget": "POST /api/budget/upload",
            "budget_status": "GET /api/budget/status/{job_id}",
        },
    }