"""Add opportunity deadline for Workspace tenders."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_workspace_deadline"
down_revision: str | None = "0008_classify_intl_sources"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("deadline_at", sa.DateTime(timezone=True)))
    op.create_index("ix_opportunities_deadline_at", "opportunities", ["deadline_at"])


def downgrade() -> None:
    op.drop_index("ix_opportunities_deadline_at", table_name="opportunities")
    op.drop_column("opportunities", "deadline_at")
