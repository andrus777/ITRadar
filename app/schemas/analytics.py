from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AnalyticsPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    label: str
    count: int


class AnalyticsDay(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    day: date
    count: int


class AnalyticsSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    days: int
    opportunities_by_day: list[AnalyticsDay]
    sources: list[AnalyticsPoint]
    categories: list[AnalyticsPoint]
    technologies: list[AnalyticsPoint]
    loaded_at: datetime
