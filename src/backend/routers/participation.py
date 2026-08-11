"""
Participation PDF upload, extraction, and matching endpoints.
"""

import json
import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ..db.database import get_db
from ..db.models import Submission, BudgetMatch, MatchStatus, Channel, ParticipationSession, BudgetLineItem, BudgetDocument, DocumentStatus
from ..schemas.participation import (
    ParticipationCheckRequest, ParticipationCheckResponse,
    MatchPointsRequest, MatchPointsResult,
)
from ..dependencies import get_classifier, get_matcher, get_embedder, get_vector_store
from ..services.classifier import ClassifierService
from ..services.matcher import MatcherService
from ..services.embedder import EmbeddingService
from ..services.vector_store import VectorStore
from ..services.participation_parser import process_participation_pdf
from ..services.participation_matcher import find_similar_participation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/participation", tags=["participation"])


@router.post("/check", response_model=ParticipationCheckResponse)
async def check_participation(
    payload: ParticipationCheckRequest,
    embedder: EmbeddingService = Depends(get_embedder),
    store: VectorStore = Depends(get_vector_store),
):
    """Check if a citizen input matches existing public participation data."""
    result = find_similar_participation(payload.text, embedder, store)
    return ParticipationCheckResponse(
        has_match=result["hasMatch"],
        boost_factor=result["boostFactor"],
        best_score=result.get("bestScore"),
        matches=result["matches"],
    )


@router.post("/upload")
async def upload_participation_pdf(
    file: UploadFile = File(...),
    county: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a public participation PDF, extract citizen input points,
    and store the session in the database.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files accepted")

    suffix = f"_{file.filename}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = process_participation_pdf(tmp_path, county=county if county else None)

        # Store session in DB (replaces the old global _participation_session)
        session = ParticipationSession(
            filename=result["filename"],
            county=result.get("county"),
            pages_parsed=result["pages_parsed"],
            points_extracted=result["points_extracted"],
            points_json=json.dumps(result["points"]),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        return {
            "session_id": session.id,
            **result,
        }

    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/match-points")
async def match_selected_points(
    payload: MatchPointsRequest,
    db: AsyncSession = Depends(get_db),
    classifier: ClassifierService = Depends(get_classifier),
    matcher: MatcherService = Depends(get_matcher),
):
    """
    Match selected citizen input points from a participation session
    against the enacted budget.
    """
    # Load session from DB
    result = await db.execute(
        select(ParticipationSession).where(ParticipationSession.id == payload.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Participation session not found. Upload a PDF first.")

    points_data = json.loads(session.points_json) if session.points_json else []
    points_map = {p["point_id"]: p for p in points_data}

    results = []
    summary = {"total": 0, "matched": 0, "partial": 0, "ignored": 0}

        # Collect all texts first
    point_texts = []
    point_pids = []
    for pid in payload.point_ids:
        point = points_map.get(pid, {})
        text = point.get("text", "").strip()
        if len(text) < 10:
            continue  # skip garbage
        point_texts.append(text)
        point_pids.append(pid)

    # ★★★ ONE API call instead of N ★★★
    if point_texts:
        classifications = await classifier.classify_batch(point_texts)
    else:
        classifications = []

    # Find budget document once (not per point)
    budget_doc = await db.execute(
        select(BudgetDocument)
        .where(BudgetDocument.status == DocumentStatus.ready)
        .order_by(desc(BudgetDocument.budget_type))
        .limit(1)
    )
    doc = budget_doc.scalar_one_or_none()
    collection = f"budget_{doc.budget_type}" if doc else "budget_proposed"

    for idx, pid in enumerate(point_pids):
        text = point_texts[idx]
        classification = classifications[idx] if idx < len(classifications) else {
            "sector": "Uncategorized", "sub_sector": "Needs Review", "confidence": 0.0
        }

        match = await matcher.match(
            citizen_text=text,
            sector=classification["sector"],
            sub_sector=classification["sub_sector"],
            ward=payload.ward,
            collection=collection,
        )

        # Persist as Submission + BudgetMatch
        submission = Submission(
            ward=payload.ward,
            channel=Channel.baraza,
            citizen_input=text[:5000],
            sector=classification["sector"],
            sub_sector=classification["sub_sector"],
            classification_confidence=classification["confidence"],
        )
        db.add(submission)
        await db.flush()

        db.add(BudgetMatch(
            submission_id=submission.id,
            matched_line_id=match.get("matched_line_id"),
            matched_sector=match.get("matched_sector"),
            matched_description=match.get("matched_description"),
            matched_amount_ksh=match.get("matched_amount_ksh"),
            source_page=match.get("source_page"),
            budget_result=match["budget_result"],
            status=MatchStatus(match["status"]),
            similarity_score=match["similarity_score"],
            simplified=match.get("simplified"),
            key_points="; ".join(match.get("key_points", [])),
            category=match.get("category"),
            alternative_matches=match.get("alternative_matches"),
        ))

        results.append({
            "point_id": pid,
            "submission_id": submission.id,
            "page_number": points_map.get(pid, {}).get("page_number"),
            "citizen_input": text,
            "sector": classification["sector"],
            "sub_sector": classification["sub_sector"],
            "budget_result": match["budget_result"],
            "status": match["status"],
            "confidence": match["similarity_score"],
            "simplified": match.get("simplified"),
            "key_points": match.get("key_points", []),
            "category": match.get("category"),
        })

        summary["total"] += 1
        summary[match["status"]] += 1

    await db.commit()
    return {"results": results, "summary": summary}