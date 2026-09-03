"""Add AI relevance decision for Telegram and other noisy sources."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_ai_relevance"
down_revision: str | None = "0014_procurement_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_analyses", sa.Column("is_opportunity", sa.Boolean()))
    op.add_column("ai_analyses", sa.Column("opportunity_probability", sa.Float()))
    op.create_check_constraint(
        "ck_ai_analyses_opportunity_probability",
        "ai_analyses",
        "opportunity_probability IS NULL OR opportunity_probability BETWEEN 0 AND 1",
    )


def downgrade() -> None:
    op.drop_constraint("ck_ai_analyses_opportunity_probability", "ai_analyses", type_="check")
    op.drop_column("ai_analyses", "opportunity_probability")
    op.drop_column("ai_analyses", "is_opportunity")
