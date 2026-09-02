from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CollectedItem(BaseModel):
    """Raw item returned by a source adapter."""

    external_id: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    payload: dict[str, Any]
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("fetched_at")
    @classmethod
    def fetched_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("fetched_at must be timezone-aware")
        return value.astimezone(UTC)


class NormalizedOpportunity(BaseModel):
    """Source-independent representation of an opportunity."""

    external_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    url: str = Field(min_length=1, max_length=2048)
    budget_from: Decimal | None = Field(default=None, ge=0)
    budget_to: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    budget_text: str | None = Field(default=None, max_length=255)
    published_at: datetime | None = None
    fetched_at: datetime
    customer_name: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    remote: bool | None = None
    status: str = Field(default="active", min_length=1, max_length=32)
    fingerprint: str = Field(min_length=64, max_length=64)

    @field_validator("published_at", "fetched_at")
    @classmethod
    def dates_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dates must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else None
