from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DashboardMetric(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    key: str
    label: str
    value: str
    detail: str | None = None


class DashboardSystemStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    key: str
    label: str
    state: str
    detail: str


class DashboardOpportunity(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    opportunity_id: int
    score: int
    title: str
    source: str
    budget: str | None
    opportunity_type: str
    published_at: datetime | None


class DashboardSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    metrics: list[DashboardMetric]
    opportunities: list[DashboardOpportunity]
    statuses: list[DashboardSystemStatus]
    loaded_at: datetime
