"""Add profile-specific opportunity workflow states."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_opportunity_user_states"
down_revision: str | None = "0015_ai_relevance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "opportunity_user_states",
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
        sa.Column("status", sa.String(length=32), server_default="new", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_profile_id",
            "opportunity_id",
            name="uq_opportunity_user_states_profile_opportunity",
        ),
        sa.CheckConstraint(
            "status IN ('new', 'interesting', 'reviewing', 'responded', "
            "'won', 'lost', 'ignored')",
            name="ck_opportunity_user_states_status",
        ),
    )
    op.create_index(
        "ix_opportunity_user_states_profile_status",
        "opportunity_user_states",
        ["user_profile_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_user_states_profile_status",
        table_name="opportunity_user_states",
    )
    op.drop_table("opportunity_user_states")
