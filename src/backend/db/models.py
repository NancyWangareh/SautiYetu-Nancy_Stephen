import uuid
from datetime import datetime
from sqlalchemy import String, Float, Text, DateTime, ForeignKey, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
import enum


class MatchStatus(str, enum.Enum):
    matched = "matched"
    partial = "partial"
    ignored = "ignored"


class Channel(str, enum.Enum):
    sms = "SMS"
    ussd = "USSD"
    whatsapp = "WhatsApp"
    web_form = "Web Form"
    baraza = "Baraza"
    voice = "Voice"
    image = "Image"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(
        String(20), primary_key=True, 
        default=lambda: f"SUB-{uuid.uuid4().hex[:5].upper()}"
    )
    ward: Mapped[str] = mapped_column(String(100), default="Umoja I")
    channel: Mapped[Channel] = mapped_column(
        SAEnum(Channel), default=Channel.web_form
    )
    citizen_input: Mapped[str] = mapped_column(Text, nullable=False)
    original_language: Mapped[str] = mapped_column(String(30), default="en")
    translated_input: Mapped[str] = mapped_column(Text, nullable=True)

    # Classification result
    sector: Mapped[str] = mapped_column(String(50), nullable=True)
    sub_sector: Mapped[str] = mapped_column(String(80), nullable=True)
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationship: one submission has one match
    match: Mapped["BudgetMatch"] = relationship(
        back_populates="submission", uselist=False, cascade="all, delete-orphan"
    )


class BudgetMatch(Base):
    __tablename__ = "budget_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("submissions.id", ondelete="CASCADE"), unique=True
    )

    # Matching result
    matched_line_id: Mapped[str] = mapped_column(String(20), nullable=True)
    matched_sector: Mapped[str] = mapped_column(String(50), nullable=True)
    matched_description: Mapped[str] = mapped_column(Text, nullable=True)
    matched_amount_ksh: Mapped[int] = mapped_column(Integer, nullable=True)
    matched_amount_requested_ksh: Mapped[int] = mapped_column(Integer, nullable=True)

    # Display text
    budget_result: Mapped[str] = mapped_column(Text, nullable=True)

    # Match quality
    status: Mapped[MatchStatus] = mapped_column(
        SAEnum(MatchStatus), default=MatchStatus.ignored
    )
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Alternative matches (top 3 results from vector search)
    alternative_matches: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array

    matched_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationship back to submission
    submission: Mapped["Submission"] = relationship(back_populates="match")
    
# ──────────────────────────────────────────────────────────────────
# Add AFTER the existing BudgetMatch class (around line 95)
# ──────────────────────────────────────────────────────────────────


class DocumentStatus(str, enum.Enum):
    uploading = "uploading"
    ready = "ready"
    failed = "failed"
    archived = "archived"


class BudgetDocument(Base):
    """Tracks uploaded budget PDFs — prevents duplicates, enables multi-doc."""
    __tablename__ = "budget_documents"

    id: Mapped[str] = mapped_column(
        String(20), primary_key=True,
        default=lambda: f"DOC-{uuid.uuid4().hex[:8].upper()}"
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    fiscal_year: Mapped[str] = mapped_column(String(20), default="2024/25")
    county: Mapped[str] = mapped_column(String(100), default="Nairobi")

    size_mb: Mapped[float] = mapped_column(nullable=False)
    total_pages: Mapped[int] = mapped_column(default=0)
    total_chunks: Mapped[int] = mapped_column(default=0)

    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus), default=DocumentStatus.uploading
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)