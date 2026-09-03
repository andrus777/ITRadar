from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.source import Source


class SourceRun(TimestampMixin, Base):
    __tablename__ = "collection_runs"
    __table_args__ = (
        Index("ix_collection_runs_status", "status"),
        Index("ix_collection_runs_source_started", "source_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="running", server_default="running")
    fetched_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    new_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error: Mapped[str | None] = mapped_column(Text)

    source: Mapped["Source"] = relationship(back_populates="collection_runs")

    @property
    def items_received(self) -> int:
        return self.fetched_count

    @property
    def items_new(self) -> int:
        return self.new_count

    @property
    def items_duplicate(self) -> int:
        return self.duplicate_count

    @property
    def items_rejected(self) -> int:
        return self.rejected_count


CollectionRun = SourceRun
