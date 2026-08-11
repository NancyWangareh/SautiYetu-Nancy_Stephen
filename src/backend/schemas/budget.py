from pydantic import BaseModel, Field
from typing import Optional


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)


class SimplifyRequest(BaseModel):
    text: str = Field(..., min_length=10)
    use_llm: bool = Field(default=False)


class SimplifyResponse(BaseModel):
    original: str
    simplified: str
    key_points: list[str]
    category: str


class DocumentResponse(BaseModel):
    id: str
    filename: str
    fiscal_year: str
    budget_type: str | None = None
    status: str
    size_mb: float
    total_pages: int
    total_chunks: int
    uploaded_at: str
    completed_at: str | None
    error_message: str | None


class IngestionStatus(BaseModel):
    job_id: str
    document_id: str
    status: str
    progress: float
    stats: dict | None = None
    error: str | None = None