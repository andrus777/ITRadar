"""Add normalized opportunity content hash for cross-source deduplication."""

import hashlib
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_opportunity_hash"
down_revision: str | None = "0011_improve_normalization"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("content_hash", sa.String(length=64)))
    opportunities = sa.table(
        "opportunities",
        sa.column("id", sa.Integer()),
        sa.column("title", sa.String()),
        sa.column("normalized_title", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("budget_text", sa.String()),
        sa.column("content_hash", sa.String()),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(
            opportunities.c.id,
            opportunities.c.title,
            opportunities.c.normalized_title,
            opportunities.c.description,
            opportunities.c.budget_text,
        )
    )
    for row in rows:
        normalized_title = (row.normalized_title or row.title).casefold()
        content = "\n".join(
            (
                normalized_title,
                (row.description or "").casefold(),
                (row.budget_text or "").casefold(),
            )
        )
        connection.execute(
            opportunities.update()
            .where(opportunities.c.id == row.id)
            .values(content_hash=hashlib.sha256(content.encode()).hexdigest())
        )
    op.alter_column("opportunities", "content_hash", nullable=False)
    op.create_index("ix_opportunities_content_hash", "opportunities", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_opportunities_content_hash", table_name="opportunities")
    op.drop_column("opportunities", "content_hash")
