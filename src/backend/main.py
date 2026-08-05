"""
FastAPI application — RAG backend for budget PDF semantic search.
"""
import csv
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import shutil
import tempfile

from .embedder import EmbeddingService
from .participation_matcher import find_similar_participation, ingest_participation
from .participation_parser import process_participation_pdf
from .simplifier import simplify_budget_line, simplify_with_llm
from .vector_store import VectorStore

# ── Load environment variables ───────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
DEEPSEEK_AVAILABLE = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())


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
    """Write a list of dicts to a CSV file. Collects all field names from all rows."""
    if not rows:
        return
    # Collect all unique field names across all rows (handles mixed old/new records)
    fieldnames = list(dict.fromkeys(
        k for row in rows for k in row.keys()
    ))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
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

def _clean_budget_text(text: str) -> str:
    """
    Normalize whitespace only — preserves the full budget line text as-is.
    """
    import re

    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned


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

        # Build enriched query: sector + sub-sector context improves semantic relevance
        if sector and sector != "Uncategorized":
            enriched_query = f"{sector}: {sub_sector}. {query_text}"
        else:
            enriched_query = query_text

        q_emb = emb.embed_query(enriched_query)
        hits = vec.search(q_emb, top_k=5)

        if not hits:
            return {
                "budgetResult": "No matching budget provision found in the enacted Nairobi County budget.",
                "status": "ignored",
                "source_page": None,
                "confidence": 0,
            }

        # Pick the best hit that has a meaningful score
        best = None
        for hit in hits:
            score = hit.get("score", 0)
            text = hit.get("text", "")
            # Skip hits that look like noise (no budget amounts, too short)
            if len(text.strip()) < 30:
                continue
            best = hit
            break

        if best is None:
            best = hits[0]

        score = best.get("score", 0)
        page = best.get("page_number", "?")
        text = best.get("text", "")

        # Preserve full budget line text with all amounts intact
        summary = _clean_budget_text(text)

        # Simplify: use DeepSeek LLM if configured, otherwise rule-based
        simplified = simplify_with_llm(summary) if DEEPSEEK_AVAILABLE else simplify_budget_line(summary)

        if score >= 0.80:
            status = "matched"
        elif score >= 0.70:
            status = "partial"
        else:
            status = "ignored"

        return {
            "budgetResult": f"p.{page} ({score:.0%} match): {summary}",
            "status": status,
            "source_page": page,
            "confidence": round(score, 3),
            # Plain-language explanation for citizens
            "simplified": simplified["simplified"],
            "keyPoints": simplified["keyPoints"],
            "category": simplified["category"],
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
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup: preload models so first request is fast ─────────────────────

@app.on_event("startup")
def _startup():
    """Preload the embedding model and connect to Qdrant at boot time."""
    import threading

    def _preload():
        # Force eager loading of the embedding model
        emb = get_embedder()
        emb._load()
        # Also connect to the vector store
        get_store()

    t = threading.Thread(target=_preload, daemon=True)
    t.start()


# ── Endpoints ────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    """Return service status."""
    return {
        "status": "ok",
        "embedder_loaded": embedder is not None and embedder.model is not None,
        "store_ready": store is not None and store.client is not None,
        "deepseek_available": DEEPSEEK_AVAILABLE,
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
    Create a new citizen submission: classify, check participation, match budget, store to CSV.

    The matching now uses a two-stage retrieval with participation boosting:
      1. Classify input by sector/sub-sector
      2. Check if similar concerns exist in public participation data
      3. Match against enacted budget via semantic search
      4. Apply participation boost factor to budget confidence

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

    # 2. Check participation data for similar community concerns
    participation = find_similar_participation(text, get_embedder(), get_store())

    # 3. Match against budget (with participation boosting)
    match = match_budget(sector, sub_sector, text)

    # Apply participation boost to budget confidence if a match exists
    if participation["hasMatch"]:
        boost = participation["boostFactor"]
        boosted_confidence = min(0.99, match.get("confidence", 0) + boost)
        match["confidence"] = round(boosted_confidence, 3)

        # Elevate status if confidence crosses thresholds
        if boosted_confidence >= 0.80 and match.get("status") != "matched":
            match["status"] = "matched"
        elif boosted_confidence >= 0.70 and match.get("status") == "ignored":
            match["status"] = "partial"

    # 4. Build record
    existing = _read_csv(SUBMISSIONS_PATH)
    next_num = 10300 + len(existing) + 1

    # Combine key points into a semicolon-separated string for CSV storage
    key_points_csv = "; ".join(match.get("keyPoints", []))

    # Serialize participation matches for CSV (compact JSON string)
    participation_json = json.dumps({
        "hasMatch": participation["hasMatch"],
        "boostFactor": participation["boostFactor"],
        "matchCount": len(participation["matches"]),
        "topMatch": participation["matches"][0]["text"][:200] if participation["matches"] else "",
    })

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
        "simplified": match.get("simplified", ""),
        "keyPoints": key_points_csv,
        "category": match.get("category", ""),
        "participation": participation_json,
    }

    # 5. Append to CSV
    existing.append(record)
    _write_csv(SUBMISSIONS_PATH, existing)

    # Return full record with detailed participation data for the frontend
    return {**record, "participationDetail": participation}


# ── Budget Simplification endpoint ───────────────────────────────────────

@app.post("/api/simplify")
def simplify_budget(payload: dict):
    """
    Translate a complex budget line into plain, citizen-friendly language.

    Expects: { "text": "Programme Based Budget: Recurrent Estimates..." }
    Returns: { "original", "simplified", "keyPoints", "category" }
    """
    text = payload.get("text", "").strip()
    if not text:
        return {"error": "Text is required"}, 400

    use_llm = payload.get("useLlm", False)

    if use_llm:
        return simplify_with_llm(text)

    return simplify_budget_line(text)


# ── Participation ingestion endpoint ────────────────────────────────────

@app.post("/api/ingest-participation")
def ingest_participation_endpoint(payload: dict | None = None):
    """
    Ingest a public participation PDF — parse, extract citizen points,
    embed, and store in the participation vector collection.

    Optional payload: { "pdf_path": "/absolute/path/to/participation.pdf" }
    """
    pdf_path = (payload or {}).get("pdf_path", None)
    stats = ingest_participation(pdf_path)
    return {"status": "completed", **stats}


# ── Real-time participation check endpoint ───────────────────────────────

@app.post("/api/participation-check")
def participation_check(payload: dict):
    """
    Real-time check: does this citizen input match any existing public
    participation points? Used for live highlighting as the user types.

    Expects: { "text": "We need a maternity wing..." }
    Returns: { hasMatch, boostFactor, matches: [...] }
    """
    text = payload.get("text", "").strip()
    if not text or len(text) < 10:
        return {"hasMatch": False, "boostFactor": 0.0, "matches": []}

    result = find_similar_participation(text, get_embedder(), get_store())
    return result


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


# ── Participation PDF Upload & Point Extraction ──────────────────────────

# In-memory store for the latest participation session (points awaiting matching)
_participation_session: dict = {}


@app.post("/api/upload-participation")
async def upload_participation_pdf(
    file: UploadFile = File(...),
    county: str = Form(""),
):
    """
    Upload a public participation PDF, extract grassroots citizen input points.

    Accepts a PDF file via multipart/form-data.
    Optional 'county' form field filters pages to only that county (e.g., "Nairobi").

    Response:
        {
            "filename": "umoja_baraza.pdf",
            "pages_parsed": 150,
            "pages_filtered": 15,
            "county": "Nairobi",
            "points_extracted": 47,
            "points": [
                { "point_id": "PT-001", "text": "...", "page_number": 3, ... },
                ...
            ]
        }
    """
    global _participation_session

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files are accepted"}, 400

    # Save uploaded file to a temporary location
    suffix = f"_{file.filename}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = process_participation_pdf(tmp_path, county=county if county else None)

        # Store session for later matching
        _participation_session = {
            "filename": result["filename"],
            "points": result["points"],
        }

        return result

    finally:
        # Clean up temporary file
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/api/match-points")
async def match_selected_points(payload: dict):
    """
    Match selected citizen input points against the enacted budget.

    Expects:
        {
            "point_ids": ["PT-001", "PT-003", ...],  # IDs of selected points
            "ward": "Umoja I"                          # optional ward context
        }

    Returns:
        {
            "results": [
                {
                    "point_id": "PT-001",
                    "citizenInput": "...",
                    "sector": "Health",
                    "subSector": "Maternal health",
                    "budgetResult": "p.143 (87% match): ...",
                    "status": "matched",
                    "simplified": "...",
                    "keyPoints": [...],
                    "category": "...",
                },
                ...
            ],
            "summary": { "total": 3, "matched": 2, "partial": 1, "ignored": 0 }
        }
    """
    global _participation_session

    point_ids = payload.get("point_ids", [])
    ward = payload.get("ward", "Not specified")

    if not point_ids:
        return {"error": "No point_ids provided"}, 400

    # Build lookup from session
    points_map = {}
    if _participation_session.get("points"):
        points_map = {p["point_id"]: p for p in _participation_session["points"]}

    results = []
    summary = {"total": 0, "matched": 0, "partial": 0, "ignored": 0}

    for pid in point_ids:
        point = points_map.get(pid, {})
        text = point.get("text", pid)

        # Classify the point
        classification = classify_text(text)
        sector = classification["sector"]
        sub_sector = classification["subSector"]

        # Match against budget
        match = match_budget(sector, sub_sector, text)

        result = {
            "point_id": pid,
            "citizenInput": text,
            "page_number": point.get("page_number"),
            "section": point.get("section", ""),
            "sector": sector,
            "subSector": sub_sector,
            "budgetResult": match["budgetResult"],
            "status": match["status"],
            "confidence": match.get("confidence", 0),
            "simplified": match.get("simplified", ""),
            "keyPoints": match.get("keyPoints", []),
            "category": match.get("category", ""),
        }

        results.append(result)
        summary["total"] += 1
        st = match.get("status", "ignored")
        if st in summary:
            summary[st] += 1

    return {"results": results, "summary": summary}


@app.get("/api/participation-session")
def get_participation_session():
    """Return the current participation session (extracted points)."""
    return _participation_session
