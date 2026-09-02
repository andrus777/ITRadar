"""Introduce unified source adapter storage fields."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_unified_source_architecture"
down_revision: str | None = "0006_add_match_notification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sources", sa.Column("source_type", sa.String(32), server_default="api", nullable=False)
    )
    op.add_column(
        "sources", sa.Column("market", sa.String(32), server_default="unknown", nullable=False)
    )
    op.add_column(
        "sources", sa.Column("priority", sa.String(8), server_default="P2", nullable=False)
    )
    op.add_column(
        "sources",
        sa.Column("collection_method", sa.String(32), server_default="api", nullable=False),
    )
    op.add_column(
        "sources",
        sa.Column("poll_interval_minutes", sa.Integer(), server_default="60", nullable=False),
    )
    op.add_column(
        "sources",
        sa.Column("health_status", sa.String(32), server_default="healthy", nullable=False),
    )
    op.add_column("sources", sa.Column("last_success_at", sa.DateTime(timezone=True)))
    op.add_column("sources", sa.Column("last_error_at", sa.DateTime(timezone=True)))
    op.add_column("sources", sa.Column("last_error", sa.Text()))
    op.add_column(
        "opportunities",
        sa.Column("opportunity_type", sa.String(32), server_default="unknown", nullable=False),
    )
    op.add_column(
        "opportunities",
        sa.Column("market", sa.String(32), server_default="unknown", nullable=False),
    )
    op.create_index("ix_opportunities_opportunity_type", "opportunities", ["opportunity_type"])
    op.create_index("ix_opportunities_market", "opportunities", ["market"])


def downgrade() -> None:
    op.drop_index("ix_opportunities_market", table_name="opportunities")
    op.drop_index("ix_opportunities_opportunity_type", table_name="opportunities")
    op.drop_column("opportunities", "market")
    op.drop_column("opportunities", "opportunity_type")
    for column in (
        "last_error",
        "last_error_at",
        "last_success_at",
        "health_status",
        "poll_interval_minutes",
        "collection_method",
        "priority",
        "market",
        "source_type",
    ):
        op.drop_column("sources", column)
