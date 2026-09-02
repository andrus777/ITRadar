"""Add developer profiles and deterministic matches."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_add_profiles_and_matches"
down_revision: str | None = "0004_add_ai_analyses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("technologies", postgresql.JSONB(), nullable=False),
        sa.Column("categories", postgresql.JSONB(), nullable=False),
        sa.Column("min_budget", sa.Numeric(14, 2)),
        sa.Column("max_budget", sa.Numeric(14, 2)),
        sa.Column("exclude_keywords", postgresql.JSONB(), nullable=False),
        sa.Column("remote_only", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "min_budget IS NULL OR max_budget IS NULL OR min_budget <= max_budget",
            name="ck_user_profiles_budget_range",
        ),
    )
    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_profile_id",
            sa.Integer(),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opportunity_id",
            sa.Integer(),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(), nullable=False),
        sa.Column(
            "matched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="ck_matches_score"),
        sa.UniqueConstraint(
            "user_profile_id", "opportunity_id", name="uq_matches_profile_opportunity"
        ),
    )
    op.create_index("ix_matches_user_profile_id", "matches", ["user_profile_id"])
    op.create_index("ix_matches_opportunity_id", "matches", ["opportunity_id"])
    op.create_index("ix_matches_score", "matches", ["score"])


def downgrade() -> None:
    op.drop_index("ix_matches_score", table_name="matches")
    op.drop_index("ix_matches_opportunity_id", table_name="matches")
    op.drop_index("ix_matches_user_profile_id", table_name="matches")
    op.drop_table("matches")
    op.drop_table("user_profiles")
