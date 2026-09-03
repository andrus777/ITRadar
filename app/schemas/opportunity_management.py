from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OpportunitySortField = Literal[
    "score", "title", "source", "type", "category", "budget", "published", "status"
]


class OpportunityFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    search: str = ""
    market: Literal["all", "ru", "international"] = "all"
    opportunity_type: str | None = None
    source: str | None = None
    category: str | None = None
    technology: str | None = None
    budget_from: Decimal | None = Field(default=None, ge=0)
    budget_to: Decimal | None = Field(default=None, ge=0)
    score_from: int | None = Field(default=None, ge=0, le=100)
    published_days: int | None = Field(default=None, ge=0, le=3650)
    status: str | None = None
    sort_by: OpportunitySortField = "published"
    sort_descending: bool = True
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=10, le=100)


class OpportunityListItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    opportunity_id: int
    score: int | None
    title: str
    source: str
    source_code: str
    opportunity_type: str
    market: str
    category: str
    technologies: list[str]
    budget: str | None
    published_at: datetime | None
    status: str


class OpportunityListPage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    items: list[OpportunityListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
