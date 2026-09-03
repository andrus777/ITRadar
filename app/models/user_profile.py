from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.match import Match
    from app.models.opportunity_user_state import OpportunityUserState


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint(
            "min_budget IS NULL OR max_budget IS NULL OR min_budget <= max_budget",
            name="ck_user_profiles_budget_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    technologies: Mapped[list[str]] = mapped_column(JSONB, default=list)
    technology_weights: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    categories: Mapped[list[str]] = mapped_column(JSONB, default=list)
    min_budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    max_budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    exclude_keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    remote_only: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    matches: Mapped[list["Match"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    opportunity_states: Mapped[list["OpportunityUserState"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
