from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.collection_run import CollectionRun
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

    raw_items: Mapped[list["RawItem"]] = relationship(back_populates="source")
    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="source")
    collection_runs: Mapped[list["CollectionRun"]] = relationship(back_populates="source")
