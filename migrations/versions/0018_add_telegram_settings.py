"""Add persistent Telegram digest settings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_telegram_settings"
down_revision: str | None = "0017_profile_technology_weights"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "telegram_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("chat_id", sa.BigInteger()),
        sa.Column("min_score", sa.Integer(), server_default="70", nullable=False),
        sa.Column("min_budget", sa.Numeric(14, 2)),
        sa.Column("max_items", sa.Integer(), server_default="20", nullable=False),
        sa.Column("include_international", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("include_types", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("min_score BETWEEN 0 AND 100", name="ck_telegram_settings_score"),
        sa.CheckConstraint("max_items BETWEEN 1 AND 100", name="ck_telegram_settings_max_items"),
        sa.CheckConstraint("id = 1", name="ck_telegram_settings_singleton"),
    )


def downgrade() -> None:
    op.drop_table("telegram_settings")
