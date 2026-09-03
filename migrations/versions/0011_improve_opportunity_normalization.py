"""Add normalized category, technologies, budget and customer types."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_improve_normalization"
down_revision: str | None = "0010_freelance_category"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("category", sa.String(length=100), server_default="other", nullable=False),
    )
    op.add_column(
        "opportunities",
        sa.Column(
            "technologies",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "opportunities",
        sa.Column("budget_type", sa.String(length=32), server_default="unknown", nullable=False),
    )
    op.add_column(
        "opportunities",
        sa.Column("customer_type", sa.String(length=32), server_default="unknown", nullable=False),
    )
    op.create_index("ix_opportunities_category", "opportunities", ["category"])


def downgrade() -> None:
    op.drop_index("ix_opportunities_category", table_name="opportunities")
    op.drop_column("opportunities", "customer_type")
    op.drop_column("opportunities", "budget_type")
    op.drop_column("opportunities", "technologies")
    op.drop_column("opportunities", "category")
