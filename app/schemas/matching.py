from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=255)
    technologies: list[str] = Field(default_factory=list, max_length=100)
    categories: list[str] = Field(default_factory=list, max_length=100)
    min_budget: Decimal | None = Field(default=None, ge=0)
    max_budget: Decimal | None = Field(default=None, ge=0)
    exclude_keywords: list[str] = Field(default_factory=list, max_length=100)
    remote_only: bool = False

    @model_validator(mode="after")
    def validate_budget_range(self) -> "UserProfileCreate":
        if (
            self.min_budget is not None
            and self.max_budget is not None
            and self.min_budget > self.max_budget
        ):
            raise ValueError("min_budget must not exceed max_budget")
        return self


class MatchReason(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    factor: Literal["technologies", "category", "budget", "remote", "blacklist"]
    matched: bool
    points: int = Field(ge=0, le=100)
    message: str


class MatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    score: int = Field(ge=0, le=100)
    reasons: list[MatchReason]
