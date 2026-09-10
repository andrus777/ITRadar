from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TelegramConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    enabled: bool
    chat_id: int | None
    min_score: int = Field(ge=0, le=100)
    min_budget: Decimal | None = Field(default=None, ge=0)
    max_items: int = Field(ge=1, le=100)
    include_international: bool
    include_types: list[str] = Field(default_factory=list, max_length=20)


class TelegramOverview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    configured: bool
    token_mask: str
    configuration: TelegramConfiguration
    last_digest_at: datetime | None
    next_digest_at: datetime | None


class TelegramActionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    message: str
    sent_count: int = Field(default=0, ge=0)
    preview: list[str] = Field(default_factory=list)
