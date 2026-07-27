from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from typing import Optional, List

from ..db.database import get_db
from ..db.models import Submission, BudgetMatch, MatchStatus

router = APIRouter(prefix="/api/matches", tags=["matches"])


class MatchResponse(BaseModel):
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
    matched_line_id: Optional[str]
    matched_amount_ksh: Optional[int]
    submitted_at: str

    class Config:
        from_attributes = True


class MatchListResponse(BaseModel):
    total: int
    matches: List[MatchResponse]


class MatchStatsResponse(BaseModel):
    total_submissions: int
    matched_count: int
    partial_count: int
    ignored_count: int
    match_rate: float  # percentage matched or partial
    by_sector: List[dict]
    by_ward: List[dict]


@router.get("", response_model=MatchListResponse)
async def list_matches(
    ward: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="matched | partial | ignored"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List all budget matches with filters.
    Called by the Matches page — the CSO's primary dashboard.
    """
    # Join submissions with their budget match
    query = select(Submission).options(selectinload(Submission.match))

    if ward:
        query = query.where(Submission.ward.ilike(f"%{ward}%"))
    if sector:
        query = query.where(Submission.sector == sector)
    if min_confidence is not None:
        query = query.where(Submission.classification_confidence >= min_confidence)

    if status:
        query = query.join(BudgetMatch).where(BudgetMatch.status == MatchStatus(status))

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Fetch
    query = query.order_by(desc(Submission.submitted_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    submissions = result.scalars().all()

    return MatchListResponse(
        total=total,
        matches=[
            MatchResponse(
                id=s.id,
                ward=s.ward,
                channel=s.channel.value,
                citizen_input=s.citizen_input,
                sector=s.sector,
                sub_sector=s.sub_sector,
                classification_confidence=s.classification_confidence,
                budget_result=s.match.budget_result if s.match else "Pending match...",
                status=s.match.status.value if s.match else "ignored",
                similarity_score=s.match.similarity_score if s.match else None,
                matched_line_id=s.match.matched_line_id if s.match else None,
                matched_amount_ksh=s.match.matched_amount_ksh if s.match else None,
                submitted_at=s.submitted_at.isoformat(),
            )
            for s in submissions
        ],
    )


@router.get("/stats", response_model=MatchStatsResponse)
async def get_match_stats(
    ward: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregate statistics for the CSO dashboard.
    Shows: total submissions, match rate, breakdown by sector and ward.
    """
    base_query = select(Submission)
    if ward:
        base_query = base_query.where(Submission.ward == ward)

    # Total submissions
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total_submissions = total_result.scalar() or 0

    if total_submissions == 0:
        return MatchStatsResponse(
            total_submissions=0,
            matched_count=0,
            partial_count=0,
            ignored_count=0,
            match_rate=0.0,
            by_sector=[],
            by_ward=[],
        )

    # Status breakdown
    status_query = (
        select(BudgetMatch.status, func.count())
        .join(Submission)
    )
    if ward:
        status_query = status_query.where(Submission.ward == ward)
    status_query = status_query.group_by(BudgetMatch.status)

    status_result = await db.execute(status_query)
    status_counts = {row[0].value: row[1] for row in status_result}

    matched = status_counts.get("matched", 0)
    partial = status_counts.get("partial", 0)
    ignored = status_counts.get("ignored", 0)

    # By sector
    sector_query = (
        select(Submission.sector, func.count())
        .where(Submission.sector.isnot(None))
    )
    if ward:
        sector_query = sector_query.where(Submission.ward == ward)
    sector_query = sector_query.group_by(Submission.sector).order_by(desc(func.count()))
    sector_result = await db.execute(sector_query)
    by_sector = [
        {"sector": row[0], "count": row[1]}
        for row in sector_result
    ]

    # By ward
    ward_query = (
        select(Submission.ward, func.count())
        .group_by(Submission.ward)
        .order_by(desc(func.count()))
        .limit(20)
    )
    ward_result = await db.execute(ward_query)
    by_ward = [
        {"ward": row[0], "count": row[1]}
        for row in ward_result
    ]

    return MatchStatsResponse(
        total_submissions=total_submissions,
        matched_count=matched,
        partial_count=partial,
        ignored_count=ignored,
        match_rate=round((matched + partial) / total_submissions * 100, 1) if total_submissions > 0 else 0.0,
        by_sector=by_sector,
        by_ward=by_ward,
    )


@router.post("/rematch/{submission_id}", response_model=MatchResponse)
async def rematch_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Re-run matching for a single submission.
    Useful when new budget data is uploaded — re-match old submissions
    against the updated budget lines.
    """
    from ..services.matcher import match_citizen_to_budget

    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(404, "Submission not found")

    # Re-run matching
    text = submission.translated_input or submission.citizen_input
    match_result = await match_citizen_to_budget(
        citizen_text=text,
        predicted_sector=submission.sector,
        predicted_sub_sector=submission.sub_sector,
        ward=submission.ward,
    )

    # Update or create match
    if submission.match:
        submission.match.matched_line_id = match_result["matched_line_id"]
        submission.match.matched_description = match_result["matched_description"]
        submission.match.matched_amount_ksh = match_result["matched_amount_ksh"]
        submission.match.budget_result = match_result["budget_result"]
        submission.match.status = MatchStatus(match_result["status"])
        submission.match.similarity_score = match_result["similarity_score"]
        submission.match.alternative_matches = match_result["alternative_matches"]
    else:
        submission.match = BudgetMatch(
            submission_id=submission.id,
            **{k: v for k, v in match_result.items() if k != "alternative_matches"},
            alternative_matches=match_result["alternative_matches"],
        )

    await db.flush()

    return MatchResponse(
        id=submission.id,
        ward=submission.ward,
        channel=submission.channel.value,
        citizen_input=submission.citizen_input,
        sector=submission.sector,
        sub_sector=submission.sub_sector,
        classification_confidence=submission.classification_confidence,
        budget_result=submission.match.budget_result,
        status=submission.match.status.value,
        similarity_score=submission.match.similarity_score,
        matched_line_id=submission.match.matched_line_id,
        matched_amount_ksh=submission.match.matched_amount_ksh,
        submitted_at=submission.submitted_at.isoformat(),
    )