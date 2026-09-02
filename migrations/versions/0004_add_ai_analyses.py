"""Add versioned AI analysis attempts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_add_ai_analyses"
down_revision: str | None = "0003_add_deduplication_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "opportunity_id",
            sa.Integer(),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("category", sa.String(length=100)),
        sa.Column("technologies", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("project_type", sa.String(length=100)),
        sa.Column("complexity", sa.Integer()),
        sa.Column("commercial_score", sa.Integer()),
        sa.Column("risk_flags", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("budget_comment", sa.Text()),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column(
            "analyzed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "complexity IS NULL OR complexity BETWEEN 1 AND 5",
            name="ck_ai_analyses_complexity",
        ),
        sa.CheckConstraint(
            "commercial_score IS NULL OR commercial_score BETWEEN 0 AND 100",
            name="ck_ai_analyses_commercial_score",
        ),
        sa.UniqueConstraint(
            "opportunity_id",
            "prompt_version",
            "input_hash",
            name="uq_ai_analyses_opportunity_prompt_input",
        ),
    )
    op.create_index("ix_ai_analyses_status", "ai_analyses", ["status"])
    op.create_index("ix_ai_analyses_analyzed_at", "ai_analyses", ["analyzed_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_analyses_analyzed_at", table_name="ai_analyses")
    op.drop_index("ix_ai_analyses_status", table_name="ai_analyses")
    op.drop_table("ai_analyses")
