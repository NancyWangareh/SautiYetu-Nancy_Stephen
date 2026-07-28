"""
FastAPI application — RAG backend for budget PDF semantic search.
"""
import csv
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .embedder import EmbeddingService
from .vector_store import VectorStore


# ── Paths ────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
BUDGET_LINES_PATH = DATA_DIR / "budget_lines.csv"
WARDS_PATH = DATA_DIR / "wards.csv"
CLASSIFICATION_RULES_PATH = DATA_DIR / "classification_rules.csv"
SUBMISSIONS_PATH = DATA_DIR / "submissons.csv"


# ── Globals (lazy-initialized on first request) ──────────────────────────
embedder: EmbeddingService | None = None
store: VectorStore | None = None


def get_embedder() -> EmbeddingService:
    global embedder
    if embedder is None:
        embedder = EmbeddingService()
    return embedder


def get_store() -> VectorStore:
    global store
    if store is None:
        store = VectorStore()
    return store


# ── CSV helpers ──────────────────────────────────────────────────────────

def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file and return a list of dicts."""
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write a list of dicts to a CSV file."""
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


# ── Classification engine (uses rules from CSV) ──────────────────────────

def classify_text(text: str) -> dict:
    """
    Classify citizen input using keyword rules from classification_rules.csv.
    Returns { sector, subSector, confidence }.
    """
    rules = _read_csv(CLASSIFICATION_RULES_PATH)
    lower = text.lower()
    best: dict | None = None  # { rule, hits }

    for rule in rules:
        keywords = [kw.strip() for kw in rule.get("keywords", "").split("|")]
        hits = sum(1 for kw in keywords if kw in lower)
        if hits > 0 and (best is None or hits > best["hits"]):
            best = {"rule": rule, "hits": hits}

    if best is None:
        return {"sector": "Uncategorized", "subSector": "Needs Review", "confidence": 0}

    return {
        "sector": best["rule"]["sector"],
        "subSector": best["rule"]["subSector"],
        "confidence": min(0.98, 0.6 + best["hits"] * 0.15),
    }


# ── Budget matching (semantic search against vector DB) ─────────────────

def match_budget(sector: str, sub_sector: str, query_text: str) -> dict:
    """
    Match a citizen request against the enacted budget PDF via semantic search.

    Uses Qdrant vector store (1,474 chunks from the Nairobi County budget PDF).
    Returns { budgetResult, status, source_page, confidence }.
    """
    try:
        emb = get_embedder()
        vec = get_store()

        if not vec.collection_exists():
            return {
                "budgetResult": "Budget document index not yet available. Please ingest the PDF first.",
                "status": "ignored",
                "source_page": None,
                "confidence": 0,
            }

        # Search with the citizen's original text for best semantic match
        q_emb = emb.embed_query(query_text)
        hits = vec.search(q_emb, top_k=3)

        if not hits:
            return {
                "budgetResult": "No matching budget provision found in the enacted Nairobi County budget.",
                "status": "ignored",
                "source_page": None,
                "confidence": 0,
            }

        top = hits[0]
        score = top.get("score", 0)
        page = top.get("page_number", "?")
        text = top.get("text", "")

        # Clean up the text excerpt for display
        excerpt = text.strip()[:250]

        # Score thresholds for status
        if score >= 0.80:
            status = "matched"
            status_label = "Found"
        elif score >= 0.70:
            status = "partial"
            status_label = "Partial match"
        else:
            status = "ignored"
            status_label = "Weak match"

        return {
            "budgetResult": f"[{status_label} · p.{page} · {score:.0%}] {excerpt}",
            "status": status,
            "source_page": page,
            "confidence": round(score, 3),
        }

    except Exception as e:
        return {
            "budgetResult": f"Budget search unavailable ({str(e)[:100]}). Request stored for review.",
            "status": "ignored",
            "source_page": None,
            "confidence": 0,
        }


# ── FastAPI app ──────────────────────────────────────────────────────────
app = FastAPI(
    title="SautiYetu RAG API",
    description="Semantic search over Nairobi County budget documents.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    """Return service status."""
    return {
        "status": "ok",
        "embedder_loaded": embedder is not None and embedder.model is not None,
        "store_ready": store is not None and store.client is not None,
    }


@app.post("/api/search")
def search(payload: dict):
    """
    Semantic search over budget document chunks.

    Expects: { "query": "maternity health budget", "top_k": 5 }
    Returns: { "results": [...], "query_time_ms": 123 }
    """
    query = payload.get("query", "").strip()
    if not query:
        return {"results": [], "query_time_ms": 0}

    top_k = payload.get("top_k", 5)

    t0 = time.perf_counter()
    emb = get_embedder()
    vec = get_store()

    query_embedding = emb.embed_query(query)
    hits = vec.search(query_embedding, top_k=top_k)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    return {"results": hits, "query_time_ms": elapsed_ms}


@app.post("/api/ingest")
def ingest(payload: dict | None = None):
    """
    (Re)ingest the budget PDF — parse, chunk, embed, store.

    Optional payload: { "pdf_path": "/absolute/path/to/budget.pdf" }
    """
    from .pipeline import run_ingestion

    pdf_path = (payload or {}).get("pdf_path", None)
    stats = run_ingestion(pdf_path)
    return {"status": "completed", **stats}


# ── CSV data endpoints ───────────────────────────────────────────────────

@app.get("/api/budget-lines")
def get_budget_lines():
    """Return all budget lines from budget_lines.csv."""
    return _read_csv(BUDGET_LINES_PATH)


@app.get("/api/wards")
def get_wards():
    """Return all wards from wards.csv."""
    return _read_csv(WARDS_PATH)


@app.get("/api/classification-rules")
def get_classification_rules():
    """Return classification rules from classification_rules.csv."""
    return _read_csv(CLASSIFICATION_RULES_PATH)


@app.get("/api/submissions")
def get_submissions():
    """Return all citizen submissions from submissons.csv."""
    return _read_csv(SUBMISSIONS_PATH)


# ── Classification endpoint ──────────────────────────────────────────────

@app.post("/api/classify")
def classify(payload: dict):
    """
    Classify a citizen input text using CSV-based keyword rules.

    Expects: { "text": "We need a maternity wing..." }
    Returns: { "sector", "subSector", "confidence" }
    """
    text = payload.get("text", "").strip()
    if not text:
        return {"sector": "Uncategorized", "subSector": "Needs Review", "confidence": 0}
    return classify_text(text)


# ── Submission endpoint (classify + match + store) ───────────────────────

@app.post("/api/submissions")
def create_submission(payload: dict):
    """
    Create a new citizen submission: classify, match budget, store to CSV.

    Expects: { "text": "...", "ward": "Umoja I", "channel": "Web Form" }
    Returns: the enriched submission record.
    """
    text = payload.get("text", "").strip()
    if not text:
        return {"error": "Text is required"}, 400

    ward = payload.get("ward", "Umoja I")
    channel = payload.get("channel", "Web Form")

    # 1. Classify
    classification = classify_text(text)
    sector = classification["sector"]
    sub_sector = classification["subSector"]

    # 2. Match against budget
    match = match_budget(sector, sub_sector, text)

    # 3. Build record
    existing = _read_csv(SUBMISSIONS_PATH)
    next_num = 10300 + len(existing) + 1
    record = {
        "id": f"SUB-{next_num}",
        "ward": ward,
        "channel": channel,
        "citizenInput": text,
        "sector": sector,
        "subSector": sub_sector,
        "budgetResult": match["budgetResult"],
        "status": match["status"],
        "submittedAt": time.strftime("%Y-%m-%d"),
    }

    # 4. Append to CSV
    existing.append(record)
    _write_csv(SUBMISSIONS_PATH, existing)

    return record
