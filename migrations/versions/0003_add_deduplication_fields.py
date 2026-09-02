"""Add normalized fields and duplicate relationships."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_deduplication_fields"
down_revision: str | None = "0002_add_budget_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("normalized_url", sa.String(length=2048)))
    op.add_column("opportunities", sa.Column("normalized_title", sa.String(length=500)))
    op.add_column(
        "opportunities",
        sa.Column("budget_negotiable", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("opportunities", sa.Column("duplicate_of_id", sa.Integer()))
    op.create_foreign_key(
        "fk_opportunities_duplicate_of",
        "opportunities",
        "opportunities",
        ["duplicate_of_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_opportunities_normalized_url", "opportunities", ["normalized_url"]
    )
    op.create_index("ix_opportunities_fingerprint", "opportunities", ["fingerprint"])
    op.create_index(
        "ix_opportunities_duplicate_of_id", "opportunities", ["duplicate_of_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_opportunities_duplicate_of_id", table_name="opportunities")
    op.drop_index("ix_opportunities_fingerprint", table_name="opportunities")
    op.drop_index("ix_opportunities_normalized_url", table_name="opportunities")
    op.drop_constraint("fk_opportunities_duplicate_of", "opportunities", type_="foreignkey")
    op.drop_column("opportunities", "duplicate_of_id")
    op.drop_column("opportunities", "budget_negotiable")
    op.drop_column("opportunities", "normalized_title")
    op.drop_column("opportunities", "normalized_url")
