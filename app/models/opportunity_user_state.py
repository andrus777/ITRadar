from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity
    from app.models.user_profile import UserProfile


class OpportunityUserState(TimestampMixin, Base):
    __tablename__ = "opportunity_user_states"
    __table_args__ = (
        UniqueConstraint(
            "user_profile_id",
            "opportunity_id",
            name="uq_opportunity_user_states_profile_opportunity",
        ),
        CheckConstraint(
            "status IN ('new', 'interesting', 'reviewing', 'responded', "
            "'won', 'lost', 'ignored')",
            name="ck_opportunity_user_states_status",
        ),
        Index("ix_opportunity_user_states_profile_status", "user_profile_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE")
    )
    opportunity_id: Mapped[int] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(32), default="new", server_default="new")

    profile: Mapped["UserProfile"] = relationship(back_populates="opportunity_states")
    opportunity: Mapped["Opportunity"] = relationship(back_populates="user_states")
