"""
CSO Report Generation — aggregated analytics for accountability.
"""

import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from ..db.database import get_db
from ..db.models import Submission, BudgetMatch, MatchStatus
from ..schemas.report import ReportResponse, ReportSummary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("")
async def generate_report(
    ward: str | None = Query(None),
    sector: str | None = Query(None),
    status: str | None = Query(None),
    date_from: str | None = Query(None, alias="dateFrom"),
    date_to: str | None = Query(None, alias="dateTo"),
    format: str = Query("json"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Submission).options(selectinload(Submission.match)).join(BudgetMatch, isouter=True)
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

    def st(s):
        return s.match.status.value if s.match else "ignored"

    matched = sum(1 for s in submissions if st(s) == "matched")
    partial = sum(1 for s in submissions if st(s) == "partial")
    ignored = sum(1 for s in submissions if st(s) == "ignored")
    total = len(submissions)

    # By sector (with status breakdown)
    by_sector_map = {}
    for s in submissions:
        k = s.sector or "Unknown"
        d = by_sector_map.setdefault(k, {"count": 0, "matched": 0, "partial": 0, "ignored": 0})
        d["count"] += 1
        d[st(s)] += 1
    by_sector = sorted(
        [{"sector": k, **v} for k, v in by_sector_map.items()],
        key=lambda x: x["count"], reverse=True,
    )

    # By ward (with status breakdown)
    by_ward_map = {}
    for s in submissions:
        k = s.ward or "Unknown"
        d = by_ward_map.setdefault(k, {"count": 0, "matched": 0, "partial": 0, "ignored": 0})
        d["count"] += 1
        d[st(s)] += 1
    by_ward = sorted(
        [{"ward": k, **v} for k, v in by_ward_map.items()],
        key=lambda x: x["count"], reverse=True,
    )

    # By channel
    channel_map = {}
    for s in submissions:
        k = s.channel.value if s.channel else "unknown"
        channel_map[k] = channel_map.get(k, 0) + 1
    by_channel = sorted(
        [{"channel": k, "count": v} for k, v in channel_map.items()],
        key=lambda x: x["count"], reverse=True,
    )

    # Top repeated requests
    request_map = {}
    for s in submissions:
        text = (s.citizen_input or "").strip()[:120]
        if not text:
            continue
        d = request_map.setdefault(text, {"count": 0, "status": "ignored"})
        d["count"] += 1
        d["status"] = st(s)
    top_requests = sorted(
        [{"text": k, "count": v["count"], "status": v["status"]} for k, v in request_map.items()],
        key=lambda x: x["count"], reverse=True,
    )[:10]

    # Available filter values
    all_wards = (await db.execute(select(Submission.ward).distinct())).scalars().all()
    all_sectors = (
        await db.execute(
            select(Submission.sector).where(Submission.sector.isnot(None)).distinct()
        )
    ).scalars().all()

    submissions_data = [
        {
            "id": s.id,
            "ward": s.ward,
            "channel": s.channel.value if s.channel else "",
            "citizenInput": s.citizen_input[:200],
            "sector": s.sector,
            "subSector": s.sub_sector,
            "status": st(s),
            "budgetResult": s.match.budget_result[:200] if s.match and s.match.budget_result else "",
            "submittedAt": s.submitted_at.isoformat() if s.submitted_at else "",
        }
        for s in submissions
    ]

    payload = {
        "filters": {
            "ward": ward, "sector": sector, "status": status,
            "date_from": date_from, "date_to": date_to,
            "available": {"wards": all_wards, "sectors": all_sectors},
        },
        "summary": {
            "total": total, "matched": matched, "partial": partial, "ignored": ignored,
            "matchRate": round((matched + partial) / total * 100, 1) if total else 0.0,
        },
        "bySector": by_sector,
        "byWard": by_ward,
        "byChannel": by_channel,
        "topRequests": top_requests,
        "fundingGap": {
            "pctAddressed": round((matched + partial) / total * 100, 1) if total else 0.0,
            "pctUnaddressed": round(ignored / total * 100, 1) if total else 0.0,
        },
        "submissions": submissions_data,
    }

    if format == "csv":
        import csv
        from io import StringIO
        output = StringIO()
        if submissions_data:
            writer = csv.DictWriter(output, fieldnames=list(submissions_data[0].keys()))
            writer.writeheader()
            writer.writerows(submissions_data)
        return {"csv": output.getvalue(), "filename": "sauti_yetu_report.csv"}

    return payload