"""Classify existing job feeds as secondary international sources."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_classify_intl_sources"
down_revision: str | None = "0007_unified_source_architecture"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_CODES = ("jobicy", "remoteok", "weworkremotely")


def upgrade() -> None:
    sources = sa.table(
        "sources",
        sa.column("id", sa.Integer()),
        sa.column("code", sa.String()),
        sa.column("market", sa.String()),
        sa.column("priority", sa.String()),
    )
    opportunities = sa.table(
        "opportunities",
        sa.column("source_id", sa.Integer()),
        sa.column("market", sa.String()),
        sa.column("opportunity_type", sa.String()),
    )
    source_ids = sa.select(sources.c.id).where(sources.c.code.in_(SOURCE_CODES))
    op.execute(
        sources.update()
        .where(sources.c.code.in_(SOURCE_CODES))
        .values(market="international", priority="P2")
    )
    op.execute(
        opportunities.update()
        .where(opportunities.c.source_id.in_(source_ids))
        .values(market="international", opportunity_type="vacancy")
    )


def downgrade() -> None:
    sources = sa.table(
        "sources",
        sa.column("id", sa.Integer()),
        sa.column("code", sa.String()),
        sa.column("market", sa.String()),
        sa.column("priority", sa.String()),
    )
    opportunities = sa.table(
        "opportunities",
        sa.column("source_id", sa.Integer()),
        sa.column("market", sa.String()),
        sa.column("opportunity_type", sa.String()),
    )
    source_ids = sa.select(sources.c.id).where(sources.c.code.in_(SOURCE_CODES))
    op.execute(
        opportunities.update()
        .where(opportunities.c.source_id.in_(source_ids))
        .values(market="unknown", opportunity_type="unknown")
    )
    op.execute(
        sources.update()
        .where(sources.c.code.in_(SOURCE_CODES))
        .values(market="unknown", priority="P2")
    )
