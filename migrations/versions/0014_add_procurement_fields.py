"""Add procurement-specific opportunity fields."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_procurement_fields"
down_revision: str | None = "0013_source_run_stats"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("procurement_number", sa.String(length=255)))
    op.add_column("opportunities", sa.Column("procurement_method", sa.String(length=255)))
    op.add_column("opportunities", sa.Column("documentation_url", sa.String(length=2048)))
    op.create_index("ix_opportunities_procurement_number", "opportunities", ["procurement_number"])


def downgrade() -> None:
    op.drop_index("ix_opportunities_procurement_number", table_name="opportunities")
    op.drop_column("opportunities", "documentation_url")
    op.drop_column("opportunities", "procurement_method")
    op.drop_column("opportunities", "procurement_number")
