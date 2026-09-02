from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.user_profile import UserProfile


class Match(TimestampMixin, Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint(
            "user_profile_id", "opportunity_id", name="uq_matches_profile_opportunity"
        ),
        CheckConstraint("score BETWEEN 0 AND 100", name="ck_matches_score"),
        Index("ix_matches_user_profile_id", "user_profile_id"),
        Index("ix_matches_opportunity_id", "opportunity_id"),
        Index("ix_matches_score", "score"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id", ondelete="CASCADE"))
    score: Mapped[int] = mapped_column(Integer)
    reasons: Mapped[list[dict[str, object]]] = mapped_column(JSONB)
    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    profile: Mapped["UserProfile"] = relationship(back_populates="matches")
    opportunity: Mapped["Opportunity"] = relationship(back_populates="matches")
