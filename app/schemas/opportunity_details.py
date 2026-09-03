from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

OpportunityUserStatus = Literal[
    "new", "interesting", "reviewing", "responded", "won", "lost", "ignored"
]


class OpportunityDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    opportunity_id: int
    title: str
    description: str | None
    source: str
    source_url: str
    published_at: datetime | None
    deadline_at: datetime | None
    budget: str | None
    category: str
    technologies: list[str]
    customer: str | None
    opportunity_type: str
    market: str
    score: int | None
    matching_reasons: list[str]
    user_status: OpportunityUserStatus
    ai_summary: str | None
    ai_category: str | None
    ai_technologies: list[str]
    complexity: int | None
    commercial_score: int | None
    risk_flags: list[str]
    budget_comment: str | None
