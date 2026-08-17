import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from ..db.database import get_db
from ..db.models import Submission, BudgetMatch, ParticipationMatch, MatchStatus, Channel
from ..schemas.submission import (
    SubmissionCreate, SubmissionResponse, SubmissionListResponse, MatchInfo,
)
from ..db.models import Submission, BudgetMatch, ParticipationMatch, MatchStatus, Channel, BudgetDocument, DocumentStatus
from ..dependencies import get_classifier, get_matcher
from ..services.classifier import ClassifierService
from ..services.matcher import MatcherService
from ..services.participation_matcher import find_similar_participation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionResponse, status_code=201)
async def create_submission(
    payload: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    classifier: ClassifierService = Depends(get_classifier),
    matcher: MatcherService = Depends(get_matcher),
):
    """Create a submission: classify → match → store. No fallbacks."""
    # 1. Classify
    classification = await classifier.classify(payload.text)
    if classification["sector"] == "Uncategorized":
        raise HTTPException(400, "Could not classify the input. Please provide more detail.")

    # 2. Create submission record
    submission = Submission(
        ward=payload.ward,
        channel=payload.channel,
        citizen_input=payload.text,
        sector=classification["sector"],
        sub_sector=classification["sub_sector"],
        classification_confidence=classification["confidence"],
    )
    db.add(submission)
    await db.flush()

    # 3. Check participation data for similar community concerns
    participation = find_similar_participation(payload.text, classifier.embedder, matcher.store)
    if participation["has_match"]:
        for pm in participation["matches"]:
            db.add(ParticipationMatch(
                submission_id=submission.id,
                point_id=pm.get("point_id", ""),
                point_text=pm.get("text", ""),
                score=pm.get("score", 0),
                boost_factor=participation["boostFactor"],
            ))
            
        # ★★★ NEW: find the active budget document for the submission's fiscal year ★★★
    fiscal_year = payload.fiscal_year or "2025/26"
    submission.fiscal_year = fiscal_year

    # Look up the most recent "ready" budget document for this fiscal year
    budget_doc_result = await db.execute(
        select(BudgetDocument)
        .where(
            BudgetDocument.fiscal_year == fiscal_year,
            BudgetDocument.status == DocumentStatus.ready,
        )
        .order_by(desc(BudgetDocument.uploaded_at))
        .limit(1)
    )
    budget_doc = budget_doc_result.scalar_one_or_none()

    # 4. Match against budget
    match_result = await matcher.match(
        citizen_text=payload.text,
        sector=classification["sector"],
        sub_sector=classification["sub_sector"],
        ward=payload.ward,
        participation_boost=participation["boostFactor"],
        document_id=budget_doc.id if budget_doc else None,
    )

    # 5. Create match record
    db.add(BudgetMatch(
        submission_id=submission.id,
        matched_line_id=match_result.get("matched_line_id"),
        matched_sector=match_result.get("matched_sector"),
        matched_description=match_result.get("matched_description"),
        matched_amount_ksh=match_result.get("matched_amount_ksh"),
        source_page=match_result.get("source_page"),
        budget_result=match_result["budget_result"],
        status=MatchStatus(match_result["status"]),
        similarity_score=match_result["similarity_score"],
        participation_boost=participation["boostFactor"],
        boosted_score=match_result.get("boosted_score", 0),
        simplified=match_result.get("simplified"),
        key_points="; ".join(match_result.get("key_points", [])),
        category=match_result.get("category"),
        alternative_matches=match_result.get("alternative_matches"),
        matched_document_id=budget_doc.id if budget_doc else None,
    ))

    await db.flush()
    await db.refresh(submission, ["match", "participation_matches"])

    logger.info("Created submission %s — status: %s", submission.id, match_result["status"])

    return _to_response(submission, participation)


@router.get("", response_model=list[SubmissionResponse])
async def list_submissions(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.match), selectinload(Submission.participation_matches))
        .order_by(desc(Submission.created_at))
        .offset(skip)
        .limit(limit)
    )
    submissions = result.scalars().all()
    return [_to_response(s) for s in submissions]


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(submission_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.match), selectinload(Submission.participation_matches))
        .where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(404, "Submission not found")
    return _to_response(submission)


@router.delete("/{submission_id}")
async def delete_submission(submission_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.match), selectinload(Submission.participation_matches))
        .where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(404, "Submission not found")

    await db.delete(submission)
    await db.commit()
    return {"message": f"Submission {submission_id} deleted", "id": submission_id}


def _to_response(submission: Submission, participation_detail: dict | None = None) -> dict:
    m = submission.match
    pm = submission.participation_matches
    return {
        "id": submission.id,
        "ward": submission.ward,
        "channel": submission.channel.value if submission.channel else "Web Form",
        "citizen_input": submission.citizen_input,
        "sector": submission.sector,
        "sub_sector": submission.sub_sector,
        "classification_confidence": submission.classification_confidence,
        "submitted_at": submission.submitted_at,
        "match": {
            "status": m.status.value if m else None,
            "budget_result": m.budget_result if m else None,
            "similarity_score": m.similarity_score if m else None,
            "simplified": m.simplified if m else None,
            "key_points": m.key_points if m else None,
            "category": m.category if m else None,
            "participation_boost": m.participation_boost if m else None,
        } if m else None,
        "participation_detail": participation_detail or {
            "has_match": bool(pm),
            "boost_factor": max((p.boost_factor for p in pm), default=0),
            "match_count": len(pm),
        },
    }