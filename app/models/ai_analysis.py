from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity


class AIAnalysis(TimestampMixin, Base):
    __tablename__ = "ai_analyses"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id",
            "prompt_version",
            "input_hash",
            name="uq_ai_analyses_opportunity_prompt_input",
        ),
        CheckConstraint(
            "complexity IS NULL OR complexity BETWEEN 1 AND 5",
            name="ck_ai_analyses_complexity",
        ),
        CheckConstraint(
            "commercial_score IS NULL OR commercial_score BETWEEN 0 AND 100",
            name="ck_ai_analyses_commercial_score",
        ),
        Index("ix_ai_analyses_status", "status"),
        Index("ix_ai_analyses_analyzed_at", "analyzed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    technologies: Mapped[list[str] | None] = mapped_column(JSONB)
    project_type: Mapped[str | None] = mapped_column(String(100))
    complexity: Mapped[int | None] = mapped_column(Integer)
    commercial_score: Mapped[int | None] = mapped_column(Integer)
    risk_flags: Mapped[list[str] | None] = mapped_column(JSONB)
    budget_comment: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(255))
    prompt_version: Mapped[str] = mapped_column(String(64))
    input_hash: Mapped[str] = mapped_column(String(64))
    error: Mapped[str | None] = mapped_column(Text)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    opportunity: Mapped["Opportunity"] = relationship(back_populates="ai_analyses")
