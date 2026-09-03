from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

OPPORTUNITY_TYPES = {"project", "freelance", "tender", "contract", "vacancy", "unknown"}
MARKETS = {"ru", "international", "unknown"}
BUDGET_TYPES = {"fixed", "hourly", "monthly", "negotiable", "unknown"}
CUSTOMER_TYPES = {"business", "government", "individual", "unknown"}


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
    source_category: str | None = Field(default=None, max_length=255)
    category: str = Field(default="other", min_length=1, max_length=100)
    technologies: list[str] = Field(default_factory=list, max_length=50)
    opportunity_type: str = Field(default="unknown", max_length=32)
    market: str = Field(default="unknown", max_length=32)
    url: str = Field(min_length=1, max_length=2048)
    normalized_url: str | None = Field(default=None, max_length=2048)
    normalized_title: str | None = Field(default=None, max_length=500)
    budget_from: Decimal | None = Field(default=None, ge=0)
    budget_to: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    budget_text: str | None = Field(default=None, max_length=255)
    budget_negotiable: bool = False
    budget_type: str = Field(default="unknown", min_length=1, max_length=32)
    published_at: datetime | None = None
    deadline_at: datetime | None = None
    fetched_at: datetime
    customer_name: str | None = Field(default=None, max_length=255)
    customer_type: str = Field(default="unknown", min_length=1, max_length=32)
    procurement_number: str | None = Field(default=None, max_length=255)
    procurement_method: str | None = Field(default=None, max_length=255)
    documentation_url: str | None = Field(default=None, max_length=2048)
    location: str | None = Field(default=None, max_length=255)
    remote: bool | None = None
    status: str = Field(default="active", min_length=1, max_length=32)
    content_hash: str = Field(default="0" * 64, min_length=64, max_length=64)
    fingerprint: str = Field(min_length=64, max_length=64)

    @field_validator("published_at", "deadline_at", "fetched_at")
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

    @field_validator("opportunity_type")
    @classmethod
    def validate_opportunity_type(cls, value: str) -> str:
        normalized = value.casefold().strip()
        if normalized not in OPPORTUNITY_TYPES:
            raise ValueError(f"unsupported opportunity_type: {value!r}")
        return normalized

    @field_validator("market")
    @classmethod
    def validate_market(cls, value: str) -> str:
        normalized = value.casefold().strip()
        if normalized not in MARKETS:
            raise ValueError(f"unsupported market: {value!r}")
        return normalized

    @field_validator("budget_type")
    @classmethod
    def validate_budget_type(cls, value: str) -> str:
        normalized = value.casefold().strip()
        if normalized not in BUDGET_TYPES:
            raise ValueError(f"unsupported budget_type: {value!r}")
        return normalized

    @field_validator("customer_type")
    @classmethod
    def validate_customer_type(cls, value: str) -> str:
        normalized = value.casefold().strip()
        if normalized not in CUSTOMER_TYPES:
            raise ValueError(f"unsupported customer_type: {value!r}")
        return normalized
