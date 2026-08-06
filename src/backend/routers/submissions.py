"""
Submissions endpoint — classify, match, and store to database.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, desc

from ..db.database import get_db
from ..db.models import Submission, BudgetMatch, MatchStatus, Channel
from ..services.classifier import classify_citizen_input
from ..services.matcher import match_citizen_to_budget

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@router.post("")
async def create_submission(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new citizen submission.
    
    1. Classify the text
    2. Match against budget (Qdrant vector search)
    3. Store both submission and match to database
    
    Request: {text, ward, channel}
    Returns: submission record with match result
    """
    text = payload.get("text", "").strip()
    if not text:
        raise HTTPException(400, "Text is required")

    ward = payload.get("ward", "Umoja I")
    channel = payload.get("channel", "Web Form")

    try:
        # 1. Classify
        logger.info(f"🏷️ Classifying: {text[:50]}...")
        classification = await classify_citizen_input(text)

        # 2. Create submission record
        submission = Submission(
            ward=ward,
            channel=channel,
            citizen_input=text,
            sector=classification["sector"],
            sub_sector=classification["sub_sector"],
            classification_confidence=classification["confidence"],
        )
        db.add(submission)
        await db.flush()  # Get ID without committing yet

        # 3. Match against budget
        logger.info(f"🔍 Matching against budget...")
        match_result = await match_citizen_to_budget(
            text,
            classification["sector"],
            classification["sub_sector"],
            ward,
        )

        # 4. Create match record
        budget_match = BudgetMatch(
            submission_id=submission.id,
            matched_line_id=match_result.get("matched_line_id"),
            matched_sector=match_result.get("matched_sector"),
            matched_description=match_result.get("matched_description"),
            matched_amount_ksh=match_result.get("matched_amount_ksh"),
            budget_result=match_result.get("budget_result"),
            status=match_result.get("status", "ignored"),
            similarity_score=match_result.get("similarity_score", 0.0),
            alternative_matches=match_result.get("alternative_matches"),
        )
        db.add(budget_match)

        # 5. Commit both
        await db.commit()
        await db.refresh(submission, ["match"])

        logger.info(f"✅ Created submission {submission.id} with status {budget_match.status}")

        return {
            "id": submission.id,
            "ward": submission.ward,
            "channel": submission.channel,
            "citizen_input": submission.citizen_input,
            "sector": submission.sector,
            "sub_sector": submission.sub_sector,
            "classification_confidence": submission.classification_confidence,
            "submitted_at": submission.submitted_at.isoformat(),
            "match": {
                "status": budget_match.status,
                "budget_result": budget_match.budget_result,
                "similarity_score": budget_match.similarity_score,
            },
        }

    except Exception as e:
        logger.error(f"Submission error: {e}")
        await db.rollback()
        raise HTTPException(500, f"Failed to create submission: {str(e)[:100]}")


@router.get("")
async def list_submissions(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    """List all submissions with their matches."""
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.match))
        .order_by(desc(Submission.created_at))
        .offset(skip)
        .limit(limit)
    )
    submissions = result.scalars().all()

    return [
        {
            "id": s.id,
            "ward": s.ward,
            "channel": s.channel,
            "citizen_input": s.citizen_input,
            "sector": s.sector,
            "sub_sector": s.sub_sector,
            "classification_confidence": s.classification_confidence,
            "submitted_at": s.submitted_at.isoformat(),
            "match": {
                "status": s.match.status if s.match else None,
                "budget_result": s.match.budget_result if s.match else None,
                "similarity_score": s.match.similarity_score if s.match else None,
            } if s.match else None,
        }
        for s in submissions
    ]


@router.get("/{submission_id}")
async def get_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific submission with its match."""
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.match))
        .where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(404, "Submission not found")

    return {
        "id": submission.id,
        "ward": submission.ward,
        "channel": submission.channel,
        "citizen_input": submission.citizen_input,
        "sector": submission.sector,
        "sub_sector": submission.sub_sector,
        "classification_confidence": submission.classification_confidence,
        "submitted_at": submission.submitted_at.isoformat(),
        "match": {
            "status": submission.match.status if submission.match else None,
            "budget_result": submission.match.budget_result if submission.match else None,
            "similarity_score": submission.match.similarity_score if submission.match else None,
        } if submission.match else None,
    }
    
# routers/submissions.py — Add this endpoint BEFORE the existing POST "" route

@router.post("/classify")
async def classify_only(payload: dict):
    """
    Lightweight classification preview — no DB write.
    Used by the frontend for real-time classification as the user types.
    """
    text = payload.get("text", "").strip()
    if not text:
        return {"sector": "Uncategorized", "sub_sector": "Needs Review", "confidence": 0.0}
    return await classify_citizen_input(text)