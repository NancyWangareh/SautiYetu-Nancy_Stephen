from pydantic import BaseModel
from typing import Optional
from ..db.models import MatchStatus


class MatchResponse(BaseModel):
    id: str
    ward: str
    channel: str
    citizen_input: str
    sector: str | None
    sub_sector: str | None
    classification_confidence: float
    budget_result: str | None
    status: MatchStatus | None
    similarity_score: float | None
    simplified: str | None = None
    key_points: str | None = None
    category: str | None = None
    participation_boost: float | None = None
    matched_line_id: str | None = None
    matched_amount_ksh: int | None = None
    submitted_at: str

    model_config = {"from_attributes": True}


class MatchListResponse(BaseModel):
    total: int
    matches: list[MatchResponse]


class MatchStatsResponse(BaseModel):
    total_submissions: int
    present_count: int
    absent_count: int
    match_rate: float
    by_sector: list[dict]
    by_ward: list[dict]