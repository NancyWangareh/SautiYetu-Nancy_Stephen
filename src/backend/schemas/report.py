from pydantic import BaseModel
from typing import Optional


class ReportFilters(BaseModel):
    ward: str | None = None
    sector: str | None = None
    status: str | None = None
    date_from: str | None = None
    date_to: str | None = None


class ReportSummary(BaseModel):
    total: int
    matched: int
    partial: int
    ignored: int
    match_rate: float


class ReportResponse(BaseModel):
    filters: dict
    summary: ReportSummary
    by_sector: list[dict]
    by_ward: list[dict]
    by_channel: list[dict]
    funding_gap: dict
    submissions: list[dict]