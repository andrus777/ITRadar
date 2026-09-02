"""Add normalized source budget text."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_budget_text"
down_revision: str | None = "0001_initial_storage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("budget_text", sa.String(length=255)))


def downgrade() -> None:
    op.drop_column("opportunities", "budget_text")
