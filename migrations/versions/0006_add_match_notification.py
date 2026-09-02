"""Track delivered match notifications."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_add_match_notification"
down_revision: str | None = "0005_add_profiles_and_matches"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("notified_at", sa.DateTime(timezone=True)))
    op.create_index("ix_matches_notified_at", "matches", ["notified_at"])


def downgrade() -> None:
    op.drop_index("ix_matches_notified_at", table_name="matches")
    op.drop_column("matches", "notified_at")
