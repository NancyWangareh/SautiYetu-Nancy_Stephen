import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from typing import Optional

from ..db.database import get_db
from ..db.models import Submission, BudgetMatch, MatchStatus
from ..schemas.match import (
    MatchResponse, MatchListResponse, MatchStatsResponse,
)
from ..dependencies import get_matcher
from ..services.matcher import MatcherService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.get("", response_model=MatchListResponse)
async def list_matches(
    ward: str | None = Query(None),
    sector: str | None = Query(None),
    status: str | None = Query(None, description="matched | partial | ignored"),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all budget matches with optional filters."""
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
                status=s.match.status if s.match else MatchStatus.ignored,
                similarity_score=s.match.similarity_score if s.match else None,
                simplified=s.match.simplified if s.match else None,
                key_points=s.match.key_points if s.match else None,
                category=s.match.category if s.match else None,
                participation_boost=s.match.participation_boost if s.match else None,
                matched_line_id=s.match.matched_line_id if s.match else None,
                matched_amount_ksh=s.match.matched_amount_ksh if s.match else None,
                submitted_at=s.submitted_at.isoformat(),
            )
            for s in submissions
        ],
    )


@router.get("/stats", response_model=MatchStatsResponse)
async def get_match_stats(
    ward: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate statistics for the CSO dashboard."""
    base_query = select(Submission)
    if ward:
        base_query = base_query.where(Submission.ward == ward)

    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total_submissions = total_result.scalar() or 0

    if total_submissions == 0:
        return MatchStatsResponse(
            total_submissions=0, matched_count=0, partial_count=0,
            ignored_count=0, match_rate=0.0, by_sector=[], by_ward=[],
        )

    # Status breakdown
    status_query = select(BudgetMatch.status, func.count()).join(Submission)
    if ward:
        status_query = status_query.where(Submission.ward == ward)
    status_query = status_query.group_by(BudgetMatch.status)
    status_result = await db.execute(status_query)
    status_counts = {row[0].value: row[1] for row in status_result}

    matched = status_counts.get("matched", 0)
    partial = status_counts.get("partial", 0)
    ignored = status_counts.get("ignored", 0)

    # By sector
    sector_query = select(Submission.sector, func.count()).where(Submission.sector.isnot(None))
    if ward:
        sector_query = sector_query.where(Submission.ward == ward)
    sector_query = sector_query.group_by(Submission.sector).order_by(desc(func.count()))
    sector_result = await db.execute(sector_query)
    by_sector = [{"sector": row[0], "count": row[1]} for row in sector_result]

    # By ward
    ward_query = select(Submission.ward, func.count()).group_by(Submission.ward).order_by(desc(func.count())).limit(20)
    ward_result = await db.execute(ward_query)
    by_ward = [{"ward": row[0], "count": row[1]} for row in ward_result]

    return MatchStatsResponse(
        total_submissions=total_submissions,
        matched_count=matched,
        partial_count=partial,
        ignored_count=ignored,
        match_rate=round((matched + partial) / total_submissions * 100, 1),
        by_sector=by_sector,
        by_ward=by_ward,
    )


@router.post("/rematch/{submission_id}", response_model=MatchResponse)
async def rematch_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
    matcher: MatcherService = Depends(get_matcher),
):
    """Re-run matching for a single submission against updated budget data."""
    result = await db.execute(
        select(Submission).options(selectinload(Submission.match)).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(404, "Submission not found")

    match_result = await matcher.match(
        citizen_text=submission.translated_input or submission.citizen_input,
        sector=submission.sector or "",
        sub_sector=submission.sub_sector or "",
        ward=submission.ward,
    )

    if submission.match:
        m = submission.match
        m.matched_line_id = match_result.get("matched_line_id")
        m.matched_description = match_result.get("matched_description")
        m.matched_amount_ksh = match_result.get("matched_amount_ksh")
        m.budget_result = match_result["budget_result"]
        m.status = MatchStatus(match_result["status"])
        m.similarity_score = match_result["similarity_score"]
        m.boosted_score = match_result.get("boosted_score", 0)
        m.simplified = match_result.get("simplified")
        m.key_points = "; ".join(match_result.get("key_points", []))
        m.category = match_result.get("category")
        m.alternative_matches = match_result.get("alternative_matches")
    else:
        submission.match = BudgetMatch(
            submission_id=submission.id,
            matched_line_id=match_result.get("matched_line_id"),
            matched_description=match_result.get("matched_description"),
            budget_result=match_result["budget_result"],
            status=MatchStatus(match_result["status"]),
            similarity_score=match_result["similarity_score"],
            boosted_score=match_result.get("boosted_score", 0),
            simplified=match_result.get("simplified"),
            key_points="; ".join(match_result.get("key_points", [])),
            category=match_result.get("category"),
            alternative_matches=match_result.get("alternative_matches"),
        )

    await db.flush()

    m = submission.match
    return MatchResponse(
        id=submission.id,
        ward=submission.ward,
        channel=submission.channel.value,
        citizen_input=submission.citizen_input,
        sector=submission.sector,
        sub_sector=submission.sub_sector,
        classification_confidence=submission.classification_confidence,
        budget_result=m.budget_result,
        status=m.status,
        similarity_score=m.similarity_score,
        simplified=m.simplified,
        key_points=m.key_points,
        category=m.category,
        participation_boost=m.participation_boost,
        matched_line_id=m.matched_line_id,
        matched_amount_ksh=m.matched_amount_ksh,
        submitted_at=submission.submitted_at.isoformat(),
    )