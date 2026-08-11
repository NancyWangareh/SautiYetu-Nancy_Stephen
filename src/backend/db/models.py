import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Float, Text, DateTime, ForeignKey, Integer, Enum as SAEnum, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


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


class DocumentStatus(str, enum.Enum):
    uploading = "uploading"
    ready = "ready"
    failed = "failed"
    archived = "archived"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(
        String(20), primary_key=True,
        default=lambda: f"SUB-{uuid.uuid4().hex[:5].upper()}"
    )
    ward: Mapped[str] = mapped_column(String(100), default="Umoja I")
    channel: Mapped[Channel] = mapped_column(SAEnum(Channel), default=Channel.web_form)
    citizen_input: Mapped[str] = mapped_column(Text, nullable=False)
    original_language: Mapped[str] = mapped_column(String(30), default="en")
    translated_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    fiscal_year: Mapped[str | None] = mapped_column(String(20), nullable=True)

    sector: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sub_sector: Mapped[str | None] = mapped_column(String(80), nullable=True)
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    match: Mapped["BudgetMatch | None"] = relationship(
        back_populates="submission", uselist=False, cascade="all, delete-orphan"
    )
    participation_matches: Mapped[list["ParticipationMatch"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class BudgetMatch(Base):
    __tablename__ = "budget_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("submissions.id", ondelete="CASCADE"), unique=True
    )

    matched_line_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    matched_sector: Mapped[str | None] = mapped_column(String(50), nullable=True)
    matched_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_amount_ksh: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    budget_result: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[MatchStatus] = mapped_column(SAEnum(MatchStatus), default=MatchStatus.ignored)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    matched_document_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Participation boost
    participation_boost: Mapped[float] = mapped_column(Float, default=0.0)
    boosted_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Plain-language
    simplified: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    alternative_matches: Mapped[str | None] = mapped_column(Text, nullable=True)

    matched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    submission: Mapped["Submission"] = relationship(back_populates="match")
    matched_line_item_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("budget_line_items.id", ondelete="SET NULL"), nullable=True
    )
    matched_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)


class BudgetDocument(Base):
    __tablename__ = "budget_documents"

    id: Mapped[str] = mapped_column(
        String(20), primary_key=True,
        default=lambda: f"DOC-{uuid.uuid4().hex[:8].upper()}"
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    fiscal_year: Mapped[str] = mapped_column(String(20), default="2024/25")
    budget_type: Mapped[str | None] = mapped_column(String(20), nullable=True, default="proposed")
    county: Mapped[str] = mapped_column(String(100), default="Nairobi")

    size_mb: Mapped[float] = mapped_column(Float, nullable=False)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[DocumentStatus] = mapped_column(SAEnum(DocumentStatus), default=DocumentStatus.uploading)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    line_items: Mapped[list["BudgetLineItem"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

class BudgetLineItem(Base):
    """Structured line items extracted from budget PDF tables."""
    __tablename__ = "budget_line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("budget_documents.id", ondelete="CASCADE"), index=True
    )
    budget_type: Mapped[str] = mapped_column(String(20), default="proposed")  # proposed | enacted
    fiscal_year: Mapped[str] = mapped_column(String(20), default="2024/25")

    page_number: Mapped[int] = mapped_column(Integer, nullable=True)

    # ── Project details ──
    s_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    project_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    delivery_unit: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── Amounts ──
    approved_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revised_i_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revised_ii_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Classification ──
    sector: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sub_sector: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # ── Source ──
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # raw table row text
    chunk_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # link to Qdrant chunk

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document: Mapped["BudgetDocument"] = relationship(back_populates="line_items")

class ParticipationSession(Base):
    """Replaces _participation_session global — database-backed."""
    __tablename__ = "participation_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    county: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pages_parsed: Mapped[int] = mapped_column(Integer, default=0)
    points_extracted: Mapped[int] = mapped_column(Integer, default=0)
    points_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON blob of extracted points
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ParticipationMatch(Base):
    """Tracks participation matches per submission."""
    __tablename__ = "participation_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("submissions.id", ondelete="CASCADE")
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participation_sessions.id", ondelete="SET NULL"), nullable=True
    )
    point_id: Mapped[str] = mapped_column(String(20), nullable=False)
    point_text: Mapped[str] = mapped_column(Text, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    boost_factor: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    submission: Mapped["Submission"] = relationship(back_populates="participation_matches")