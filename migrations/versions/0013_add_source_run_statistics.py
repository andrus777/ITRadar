"""Add duplicate and rejected counters to source runs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_source_run_stats"
down_revision: str | None = "0012_opportunity_hash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "collection_runs",
        sa.Column("duplicate_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "collection_runs",
        sa.Column("rejected_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index(
        "ix_collection_runs_source_started",
        "collection_runs",
        ["source_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_collection_runs_source_started", table_name="collection_runs")
    op.drop_column("collection_runs", "rejected_count")
    op.drop_column("collection_runs", "duplicate_count")
