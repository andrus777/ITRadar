"""Add technology weights to developer profiles."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_profile_technology_weights"
down_revision: str | None = "0016_opportunity_user_states"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("technology_weights", postgresql.JSONB(), nullable=True),
    )
    op.execute("UPDATE user_profiles SET technology_weights = '{}'::jsonb")
    op.alter_column("user_profiles", "technology_weights", nullable=False)


def downgrade() -> None:
    op.drop_column("user_profiles", "technology_weights")
