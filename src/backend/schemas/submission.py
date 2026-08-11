from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from ..db.models import MatchStatus, Channel


class SubmissionCreate(BaseModel):
    text: str = Field(..., min_length=5, max_length=5000)
    ward: str = Field(default="Umoja I", max_length=100)
    channel: Channel = Field(default=Channel.web_form)
    fiscal_year: str = Field(default="2025/26", max_length=20)


class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=5000)


class ClassifyResponse(BaseModel):
    sector: str
    sub_sector: str
    confidence: float


class MatchInfo(BaseModel):
    status: MatchStatus | None
    budget_result: str | None
    similarity_score: float | None = None
    simplified: str | None = None
    key_points: str | None = None
    category: str | None = None
    participation_boost: float | None = None


class SubmissionResponse(BaseModel):
    id: str
    ward: str
    channel: str
    citizen_input: str
    sector: str | None
    sub_sector: str | None
    classification_confidence: float
    submitted_at: datetime
    match: MatchInfo | None
    participation_detail: dict | None = None

    model_config = {"from_attributes": True}


class SubmissionListResponse(BaseModel):
    total: int
    submissions: list[SubmissionResponse]