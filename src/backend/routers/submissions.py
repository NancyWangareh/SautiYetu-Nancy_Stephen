from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from ..db.database import get_db
from ..db.models import Submission, BudgetMatch, Channel, MatchStatus
from ..services.classifier import classify_citizen_input
from ..services.translator import translate_to_english
from ..services.matcher import match_citizen_to_budget

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


# ── Request / Response Schemas ──

class SubmissionCreate(BaseModel):
    text: str = Field(..., min_length=5, max_length=2000, description="Citizen's raw input text")
    ward: str = Field(default="Umoja I", max_length=100)
    channel: str = Field(default="Web Form", pattern="^(SMS|USSD|WhatsApp|Web Form|Baraza|Voice|Image)$")


class ClassificationPreview(BaseModel):
    text: str = Field(..., min_length=5, max_length=2000)


class SubmissionResponse(BaseModel):
    id: str
    ward: str
    channel: str
    citizen_input: str
    sector: Optional[str]
    sub_sector: Optional[str]
    classification_confidence: float
    budget_result: Optional[str]
    status: Optional[str]
    similarity_score: Optional[float]
    submitted_at: str

    class Config:
        from_attributes = True


class SubmissionListResponse(BaseModel):
    total: int
    submissions: List[SubmissionResponse]


class ClassifyResponse(BaseModel):
    sector: str
    sub_sector: str
    confidence: float
    reasoning: str


# ── Endpoints ──

@router.post("/classify", response_model=ClassifyResponse)
async def classify_text(payload: ClassificationPreview):
    """
    Live classification preview — called as the user types in the Input page.
    Returns sector, sub_sector, and confidence without saving anything.
    """
    result = await classify_citizen_input(payload.text)
    return ClassifyResponse(**result)


@router.post("", response_model=SubmissionResponse, status_code=201)
async def create_submission(
    payload: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Full submission pipeline:
    1. Translate Sheng/Swahili if needed
    2. Classify with DeepSeek
    3. Match against budget lines in Pinecone
    4. Save to PostgreSQL
    5. Return the complete result
    
    Called by: Web form, SMS webhook, USSD webhook, WhatsApp webhook.
    """
    # ── Step 1: Translate if needed ──
    translation = await translate_to_english(payload.text)
    clean_text = translation["translated_text"]

    # ── Step 2: Classify ──
    classification = await classify_citizen_input(clean_text)

    # ── Step 3: Match against budget ──
    match_result = await match_citizen_to_budget(
        citizen_text=clean_text,
        predicted_sector=classification["sector"],
        predicted_sub_sector=classification["sub_sector"],
        ward=payload.ward,
    )

    # ── Step 4: Persist ──
    submission = Submission(
        ward=payload.ward,
        channel=Channel(payload.channel),
        citizen_input=payload.text,  # Store original text
        original_language=translation["original_language"],
        translated_input=clean_text if translation["was_translated"] else None,
        sector=classification["sector"],
        sub_sector=classification["sub_sector"],
        classification_confidence=classification["confidence"],
    )
    db.add(submission)
    await db.flush()  # Get the generated ID

    budget_match = BudgetMatch(
        submission_id=submission.id,
        matched_line_id=match_result["matched_line_id"],
        matched_sector=match_result["matched_sector"],
        matched_description=match_result["matched_description"],
        matched_amount_ksh=match_result["matched_amount_ksh"],
        matched_amount_requested_ksh=match_result["matched_amount_requested_ksh"],
        budget_result=match_result["budget_result"],
        status=MatchStatus(match_result["status"]),
        similarity_score=match_result["similarity_score"],
        alternative_matches=match_result["alternative_matches"],
    )
    db.add(budget_match)

    await db.flush()

    return SubmissionResponse(
        id=submission.id,
        ward=submission.ward,
        channel=submission.channel.value,
        citizen_input=submission.citizen_input,
        sector=submission.sector,
        sub_sector=submission.sub_sector,
        classification_confidence=submission.classification_confidence,
        budget_result=budget_match.budget_result,
        status=budget_match.status.value,
        similarity_score=budget_match.similarity_score,
        submitted_at=submission.submitted_at.isoformat(),
    )


@router.get("", response_model=SubmissionListResponse)
async def list_submissions(
    ward: Optional[str] = Query(None, description="Filter by ward"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    status: Optional[str] = Query(None, description="Filter by match status"),
    search: Optional[str] = Query(None, description="Search in citizen input"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List all submissions with optional filters.
    Called by the Submissions page and CSO dashboard.
    """
    query = select(Submission).options(selectinload(Submission.match))

    if ward:
        query = query.where(Submission.ward.ilike(f"%{ward}%"))
    if sector:
        query = query.where(Submission.sector == sector)
    if channel:
        query = query.where(Submission.channel == Channel(channel))
    if search:
        query = query.where(Submission.citizen_input.ilike(f"%{search}%"))

    # Status filter requires joining with BudgetMatch
    if status:
        query = (
            query.join(BudgetMatch)
            .where(BudgetMatch.status == MatchStatus(status))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Fetch page
    query = query.order_by(desc(Submission.submitted_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    submissions = result.scalars().all()

    return SubmissionListResponse(
        total=total,
        submissions=[
            SubmissionResponse(
                id=s.id,
                ward=s.ward,
                channel=s.channel.value,
                citizen_input=s.citizen_input,
                sector=s.sector,
                sub_sector=s.sub_sector,
                classification_confidence=s.classification_confidence,
                budget_result=s.match.budget_result if s.match else None,
                status=s.match.status.value if s.match else None,
                similarity_score=s.match.similarity_score if s.match else None,
                submitted_at=s.submitted_at.isoformat(),
            )
            for s in submissions
        ],
    )


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single submission with its match."""
    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(404, f"Submission {submission_id} not found")

    return SubmissionResponse(
        id=submission.id,
        ward=submission.ward,
        channel=submission.channel.value,
        citizen_input=submission.citizen_input,
        sector=submission.sector,
        sub_sector=submission.sub_sector,
        classification_confidence=submission.classification_confidence,
        budget_result=submission.match.budget_result if submission.match else None,
        status=submission.match.status.value if submission.match else None,
        similarity_score=submission.match.similarity_score if submission.match else None,
        submitted_at=submission.submitted_at.isoformat(),
    )