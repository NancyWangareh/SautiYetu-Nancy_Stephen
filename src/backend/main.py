from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db.database import init_db
from .routers import budget, submissions, matches


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(budget.router)
app.include_router(submissions.router)
app.include_router(matches.router)


@app.get("/")
async def root():
    return {"service": "SautiYetu API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}