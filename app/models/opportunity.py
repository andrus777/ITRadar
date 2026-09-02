from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.ai_analysis import AIAnalysis
    from app.models.match import Match
    from app.models.source import Source


class Opportunity(TimestampMixin, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_opportunities_source_external"),
        Index("ix_opportunities_published_at", "published_at"),
        Index("ix_opportunities_fetched_at", "fetched_at"),
        Index("ix_opportunities_status", "status"),
        Index("ix_opportunities_normalized_url", "normalized_url"),
        Index("ix_opportunities_fingerprint", "fingerprint"),
        Index("ix_opportunities_duplicate_of_id", "duplicate_of_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    external_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    opportunity_type: Mapped[str] = mapped_column(
        String(32), default="unknown", server_default="unknown"
    )
    market: Mapped[str] = mapped_column(String(32), default="unknown", server_default="unknown")
    url: Mapped[str] = mapped_column(String(2048))
    normalized_url: Mapped[str | None] = mapped_column(String(2048))
    normalized_title: Mapped[str | None] = mapped_column(String(500))
    budget_from: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    budget_to: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    budget_text: Mapped[str | None] = mapped_column(String(255))
    budget_negotiable: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    customer_name: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    remote: Mapped[bool | None] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(32), default="active", server_default="active")
    fingerprint: Mapped[str] = mapped_column(String(64))
    duplicate_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("opportunities.id", ondelete="SET NULL")
    )

    source: Mapped["Source"] = relationship(back_populates="opportunities")
    duplicate_of: Mapped["Opportunity | None"] = relationship(
        remote_side="Opportunity.id",
        foreign_keys=[duplicate_of_id],
        back_populates="duplicates",
    )
    duplicates: Mapped[list["Opportunity"]] = relationship(
        foreign_keys=[duplicate_of_id],
        back_populates="duplicate_of",
    )
    ai_analyses: Mapped[list["AIAnalysis"]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )
    matches: Mapped[list["Match"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )
