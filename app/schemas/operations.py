from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CollectionRunStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    run_id: int
    source: str
    status: str
    fetched_count: int
    new_count: int
    started_at: datetime
    finished_at: datetime | None
    error: str | None


class HealthStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    status: str
    database: str


class ReadinessStatus(HealthStatus):
    collection_runs: list[CollectionRunStatus]
