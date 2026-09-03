"""Add source category for Freelance.ru tasks."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_freelance_category"
down_revision: str | None = "0009_workspace_deadline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("source_category", sa.String(length=255)))
    op.create_index("ix_opportunities_source_category", "opportunities", ["source_category"])


def downgrade() -> None:
    op.drop_index("ix_opportunities_source_category", table_name="opportunities")
    op.drop_column("opportunities", "source_category")
