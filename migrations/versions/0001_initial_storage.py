"""Create initial opportunity storage tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_storage"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamp_columns(),
        sa.UniqueConstraint("code", name="uq_sources_code"),
    )
    op.create_index("ix_sources_code", "sources", ["code"])

    op.create_table(
        "raw_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        *timestamp_columns(),
        sa.UniqueConstraint(
            "source_id", "external_id", name="uq_raw_items_source_external"
        ),
    )
    op.create_index("ix_raw_items_fetched_at", "raw_items", ["fetched_at"])

    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("budget_from", sa.Numeric(precision=14, scale=2)),
        sa.Column("budget_to", sa.Numeric(precision=14, scale=2)),
        sa.Column("currency", sa.String(length=3)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("customer_name", sa.String(length=255)),
        sa.Column("location", sa.String(length=255)),
        sa.Column("remote", sa.Boolean()),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        *timestamp_columns(),
        sa.UniqueConstraint(
            "source_id", "external_id", name="uq_opportunities_source_external"
        ),
    )
    op.create_index("ix_opportunities_published_at", "opportunities", ["published_at"])
    op.create_index("ix_opportunities_fetched_at", "opportunities", ["fetched_at"])
    op.create_index("ix_opportunities_status", "opportunities", ["status"])

    op.create_table(
        "collection_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=32), server_default="running", nullable=False),
        sa.Column("fetched_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("new_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error", sa.Text()),
        *timestamp_columns(),
    )
    op.create_index("ix_collection_runs_status", "collection_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_collection_runs_status", table_name="collection_runs")
    op.drop_table("collection_runs")
    op.drop_index("ix_opportunities_status", table_name="opportunities")
    op.drop_index("ix_opportunities_fetched_at", table_name="opportunities")
    op.drop_index("ix_opportunities_published_at", table_name="opportunities")
    op.drop_table("opportunities")
    op.drop_index("ix_raw_items_fetched_at", table_name="raw_items")
    op.drop_table("raw_items")
    op.drop_index("ix_sources_code", table_name="sources")
    op.drop_table("sources")
