from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class TelegramSettings(TimestampMixin, Base):
    __tablename__ = "telegram_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_telegram_settings_singleton"),
        CheckConstraint("min_score BETWEEN 0 AND 100", name="ck_telegram_settings_score"),
        CheckConstraint("max_items BETWEEN 1 AND 100", name="ck_telegram_settings_max_items"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    chat_id: Mapped[int | None] = mapped_column(BigInteger)
    min_score: Mapped[int] = mapped_column(Integer, default=70, server_default="70")
    min_budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    max_items: Mapped[int] = mapped_column(Integer, default=20, server_default="20")
    include_international: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    include_types: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
