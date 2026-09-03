from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CollectionRunStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    run_id: int
    source: str
    status: str
    fetched_count: int
    new_count: int
    duplicate_count: int
    rejected_count: int
    items_received: int
    items_new: int
    items_duplicate: int
    items_rejected: int
    health: str
    last_success_at: datetime | None
    last_error_at: datetime | None
    started_at: datetime
    finished_at: datetime | None
    error: str | None


class HealthStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    status: str
    database: str


class ReadinessStatus(HealthStatus):
    collection_runs: list[CollectionRunStatus]
