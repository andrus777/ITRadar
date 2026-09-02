from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OpportunityCard(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    opportunity_id: int
    title: str
    budget: str | None
    source_name: str
    source_url: str
    summary: str | None
    score: int | None
    reasons: list[str]
    published_at: datetime | None


class OpportunityPage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    card: OpportunityCard | None
    page: int
    has_previous: bool
    has_next: bool


class ProfileView(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    technologies: list[str]
    categories: list[str]
    min_budget: str | None
    max_budget: str | None
    exclude_keywords: list[str]
    remote_only: bool
