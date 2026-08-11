"""
CSO Report Generation — aggregated analytics for accountability.
"""

import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from ..db.database import get_db
from ..db.models import Submission, BudgetMatch, MatchStatus
from ..schemas.report import ReportResponse, ReportSummary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=ReportResponse)
async def generate_report(
    ward: str | None = Query(None),
    sector: str | None = Query(None),
    status: str | None = Query(None),
    date_from: str | None = Query(None, alias="dateFrom"),
    date_to: str | None = Query(None, alias="dateTo"),
    format: str = Query("json"),
    db: AsyncSession = Depends(get_db),
):
    """Generate an aggregated CSO report with optional filters."""
    # Base query
    query = select(Submission).join(BudgetMatch, isouter=True)

    if ward:
        query = query.where(Submission.ward.ilike(f"%{ward}%"))
    if sector:
        query = query.where(Submission.sector == sector)
    if status:
        query = query.where(BudgetMatch.status == MatchStatus(status))
    if date_from:
        query = query.where(Submission.submitted_at >= date_from)
    if date_to:
        query = query.where(Submission.submitted_at <= date_to)

    result = await db.execute(query)
    submissions = result.scalars().all()

    # Build summary
    matched = sum(1 for s in submissions if s.match and s.match.status == MatchStatus.matched)
    partial = sum(1 for s in submissions if s.match and s.match.status == MatchStatus.partial)
    ignored = sum(1 for s in submissions if s.match and s.match.status == MatchStatus.ignored)
    total = len(submissions)

    summary = ReportSummary(
        total=total,
        matched=matched,
        partial=partial,
        ignored=ignored,
        match_rate=round((matched + partial) / total * 100, 1) if total > 0 else 0.0,
    )

    # By sector
    sector_counts: dict[str, int] = {}
    for s in submissions:
        if s.sector:
            sector_counts[s.sector] = sector_counts.get(s.sector, 0) + 1
    by_sector = sorted(
        [{"sector": k, "count": v} for k, v in sector_counts.items()],
        key=lambda x: x["count"], reverse=True,
    )

    # By ward
    ward_counts: dict[str, int] = {}
    for s in submissions:
        ward_counts[s.ward] = ward_counts.get(s.ward, 0) + 1
    by_ward = sorted(
        [{"ward": k, "count": v} for k, v in ward_counts.items()],
        key=lambda x: x["count"], reverse=True,
    )

    # By channel
    channel_counts: dict[str, int] = {}
    for s in submissions:
        ch = s.channel.value if s.channel else "unknown"
        channel_counts[ch] = channel_counts.get(ch, 0) + 1
    by_channel = sorted(
        [{"channel": k, "count": v} for k, v in channel_counts.items()],
        key=lambda x: x["count"], reverse=True,
    )

    # Funding gap
    funding_gap = {
        "matched_count": matched,
        "partial_count": partial,
        "ignored_count": ignored,
        "pct_addressed": round((matched + partial) / total * 100, 1) if total > 0 else 0.0,
        "pct_ignored": round(ignored / total * 100, 1) if total > 0 else 0.0,
    }

    # Submissions data
    submissions_data = [
        {
            "id": s.id,
            "ward": s.ward,
            "channel": s.channel.value if s.channel else "",
            "citizen_input": s.citizen_input[:200],
            "sector": s.sector,
            "sub_sector": s.sub_sector,
            "status": s.match.status.value if s.match else "ignored",
            "budget_result": s.match.budget_result[:200] if s.match and s.match.budget_result else "",
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else "",
        }
        for s in submissions
    ]

    # CSV export
    if format == "csv":
        import csv
        from io import StringIO

        output = StringIO()
        if submissions_data:
            writer = csv.DictWriter(output, fieldnames=list(submissions_data[0].keys()))
            writer.writeheader()
            writer.writerows(submissions_data)

        from fastapi.responses import Response
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=sauti_yetu_report.csv"},
        )

    return ReportResponse(
        filters={"ward": ward, "sector": sector, "status": status, "date_from": date_from, "date_to": date_to},
        summary=summary,
        by_sector=by_sector,
        by_ward=by_ward,
        by_channel=by_channel,
        funding_gap=funding_gap,
        submissions=submissions_data,
    )