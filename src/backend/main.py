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
<<<<<<< HEAD

def _clean_budget_text(text: str) -> str:
    """
    Normalize whitespace only — preserves the full budget line text as-is.
    """
    import re

    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned

=======
>>>>>>> 49a3f42739e9d47cb6cfb6133f7ab2dd9a65f243

def match_budget(sector: str, sub_sector: str, query_text: str) -> dict:
    """
    Match a citizen request against the enacted budget PDF via semantic search.
<<<<<<< HEAD
=======

    Uses Qdrant vector store (1,474 chunks from the Nairobi County budget PDF).
>>>>>>> 49a3f42739e9d47cb6cfb6133f7ab2dd9a65f243
    Returns { budgetResult, status, source_page, confidence }.
    """
    try:
        emb = get_embedder()
        vec = get_store()

        if not vec.collection_exists():
            return {
<<<<<<< HEAD
                "budgetResult": "Budget index unavailable. Ingest the PDF first.",
=======
                "budgetResult": "Budget document index not yet available. Please ingest the PDF first.",
>>>>>>> 49a3f42739e9d47cb6cfb6133f7ab2dd9a65f243
                "status": "ignored",
                "source_page": None,
                "confidence": 0,
            }

<<<<<<< HEAD
=======
        # Search with the citizen's original text for best semantic match
>>>>>>> 49a3f42739e9d47cb6cfb6133f7ab2dd9a65f243
        q_emb = emb.embed_query(query_text)
        hits = vec.search(q_emb, top_k=3)

        if not hits:
            return {
<<<<<<< HEAD
                "budgetResult": "No matching budget provision found.",
=======
                "budgetResult": "No matching budget provision found in the enacted Nairobi County budget.",
>>>>>>> 49a3f42739e9d47cb6cfb6133f7ab2dd9a65f243
                "status": "ignored",
                "source_page": None,
                "confidence": 0,
            }

        top = hits[0]
        score = top.get("score", 0)
        page = top.get("page_number", "?")
        text = top.get("text", "")

<<<<<<< HEAD
        # Clean and simplify for citizen display
        summary = _clean_budget_text(text)

        if score >= 0.80:
            status = "matched"
        elif score >= 0.70:
            status = "partial"
        else:
            status = "ignored"

        return {
            "budgetResult": f"p.{page} ({score:.0%} match): {summary}",
=======
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
>>>>>>> 49a3f42739e9d47cb6cfb6133f7ab2dd9a65f243
            "status": status,
            "source_page": page,
            "confidence": round(score, 3),
        }

    except Exception as e:
        return {
<<<<<<< HEAD
            "budgetResult": f"Budget search unavailable. Request stored for review.",
=======
            "budgetResult": f"Budget search unavailable ({str(e)[:100]}). Request stored for review.",
>>>>>>> 49a3f42739e9d47cb6cfb6133f7ab2dd9a65f243
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


# ── Report Generation for CSOs ───────────────────────────────────────────

@app.get("/api/report")
def generate_report(
    ward: str | None = None,
    sector: str | None = None,
    status: str | None = None,
    dateFrom: str | None = None,
    dateTo: str | None = None,
    format: str = "json",
):
    """
    Generate an aggregated report for Civil Society Organisations (CSOs).

    Query params (all optional filters):
      - ward:       filter by ward name
      - sector:     filter by sector
      - status:     filter by status (matched | partial | ignored)
      - dateFrom:   filter submissions on or after this date (YYYY-MM-DD)
      - dateTo:     filter submissions on or before this date (YYYY-MM-DD)
      - format:     "json" (default) or "csv"

    Returns:
      {
        filters: { ... },
        summary: { total, matched, partial, ignored },
        bySector: [...],
        byWard: [...],
        byChannel: [...],
        byStatus: {...},
        fundingGap: { matchedCount, partialCount, ignoredCount, pctAddressed },
        submissions: [ ... filtered records ],
      }
    """
    import re as _re

    all_rows = _read_csv(SUBMISSIONS_PATH)

    # Apply filters
    filtered = []
    for row in all_rows:
        if ward and row.get("ward", "").strip().lower() != ward.strip().lower():
            continue
        if sector and row.get("sector", "").strip().lower() != sector.strip().lower():
            continue
        if status and row.get("status", "").strip().lower() != status.strip().lower():
            continue
        row_date = row.get("submittedAt", "")
        if dateFrom and row_date < dateFrom:
            continue
        if dateTo and row_date > dateTo:
            continue
        filtered.append(row)

    total = len(filtered)

    # ── By Status ──
    by_status = {"matched": 0, "partial": 0, "ignored": 0}
    for r in filtered:
        st = r.get("status", "ignored")
        if st in by_status:
            by_status[st] += 1

    # ── By Sector ──
    sector_map: dict[str, dict] = {}
    for r in filtered:
        sec = r.get("sector", "Uncategorized")
        if sec not in sector_map:
            sector_map[sec] = {"sector": sec, "count": 0, "matched": 0, "partial": 0, "ignored": 0}
        sector_map[sec]["count"] += 1
        st = r.get("status", "ignored")
        if st in ("matched", "partial", "ignored"):
            sector_map[sec][st] += 1

    by_sector = sorted(sector_map.values(), key=lambda x: x["count"], reverse=True)

    # ── By Ward ──
    ward_map: dict[str, dict] = {}
    for r in filtered:
        w = r.get("ward", "Unknown")
        if w not in ward_map:
            ward_map[w] = {"ward": w, "count": 0, "matched": 0, "partial": 0, "ignored": 0}
        ward_map[w]["count"] += 1
        st = r.get("status", "ignored")
        if st in ("matched", "partial", "ignored"):
            ward_map[w][st] += 1

    by_ward = sorted(ward_map.values(), key=lambda x: x["count"], reverse=True)

    # ── By Channel ──
    channel_map: dict[str, int] = {}
    for r in filtered:
        ch = r.get("channel", "Unknown")
        channel_map[ch] = channel_map.get(ch, 0) + 1

    by_channel = [{"channel": k, "count": v} for k, v in sorted(channel_map.items(), key=lambda x: x[1], reverse=True)]

    # ── Funding Gap ──
    pct_addressed = round((by_status["matched"] / total * 100), 1) if total > 0 else 0
    funding_gap = {
        "matchedCount": by_status["matched"],
        "partialCount": by_status["partial"],
        "ignoredCount": by_status["ignored"],
        "pctAddressed": pct_addressed,
        "pctUnaddressed": round(100 - pct_addressed, 1),
    }

    # ── Top Requests ──
    request_counts: dict[str, dict] = {}
    for r in filtered:
        text = r.get("citizenInput", "").strip().lower()
        if text:
            if text not in request_counts:
                request_counts[text] = {"text": r.get("citizenInput", ""), "count": 0, "ward": r.get("ward", ""), "status": r.get("status", "")}
            request_counts[text]["count"] += 1

    top_requests = sorted(request_counts.values(), key=lambda x: x["count"], reverse=True)[:10]

    # ── Available filters ──
    all_wards = sorted({r.get("ward", "") for r in all_rows if r.get("ward")})
    all_sectors = sorted({r.get("sector", "") for r in all_rows if r.get("sector")})
    all_statuses = ["matched", "partial", "ignored"]

    report = {
        "filters": {
            "applied": {"ward": ward, "sector": sector, "status": status, "dateFrom": dateFrom, "dateTo": dateTo},
            "available": {"wards": all_wards, "sectors": all_sectors, "statuses": all_statuses},
        },
        "summary": {
            "total": total,
            "matched": by_status["matched"],
            "partial": by_status["partial"],
            "ignored": by_status["ignored"],
        },
        "bySector": by_sector,
        "byWard": by_ward,
        "byChannel": by_channel,
        "byStatus": by_status,
        "fundingGap": funding_gap,
        "topRequests": top_requests,
        "submissions": filtered if format != "csv" else [],
    }

    # ── CSV export ──
    if format == "csv":
        from io import StringIO
        import csv as _csv

        output = StringIO()
        if filtered:
            writer = _csv.DictWriter(output, fieldnames=list(filtered[0].keys()))
            writer.writeheader()
            writer.writerows(filtered)
        return {"csv": output.getvalue(), "filename": f"sauti_yetu_report_{time.strftime('%Y%m%d')}.csv"}

    return report
