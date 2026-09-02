from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.collection_run import SourceRun
    from app.models.opportunity import Opportunity
    from app.models.raw_item import RawItem


class Source(TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("code", name="uq_sources_code"),
        Index("ix_sources_code", "code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    base_url: Mapped[str] = mapped_column(String(2048))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    source_type: Mapped[str] = mapped_column(String(32), default="api", server_default="api")
    market: Mapped[str] = mapped_column(String(32), default="unknown", server_default="unknown")
    priority: Mapped[str] = mapped_column(String(8), default="P2", server_default="P2")
    collection_method: Mapped[str] = mapped_column(String(32), default="api", server_default="api")
    poll_interval_minutes: Mapped[int] = mapped_column(Integer, default=60, server_default="60")
    health_status: Mapped[str] = mapped_column(
        String(32), default="healthy", server_default="healthy"
    )
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    raw_items: Mapped[list["RawItem"]] = relationship(back_populates="source")
    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="source")
    collection_runs: Mapped[list["SourceRun"]] = relationship(back_populates="source")
