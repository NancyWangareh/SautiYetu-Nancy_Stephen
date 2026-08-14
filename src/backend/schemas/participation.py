from pydantic import BaseModel, Field
from typing import Optional


class ParticipationCheckRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)


class ParticipationCheckResponse(BaseModel):
    has_match: bool
    boost_factor: float
    best_score: float | None = None
    matches: list[dict] = []


class MatchPointsRequest(BaseModel):
    point_ids: list[str] = Field(..., min_length=1)
    ward: str | None = Field(default=None)  # optional fallback; per-point section wins
    session_id: str = Field(...)  # Database-backed session ID


class MatchPointsResult(BaseModel):
    point_id: str
    citizen_input: str
    sector: str
    sub_sector: str
    budget_result: str
    status: str
    confidence: float
    simplified: str | None = None
    key_points: list[str] | None = None
    category: str | None = None