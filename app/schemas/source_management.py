from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    source_id: int
    code: str
    name: str
    base_url: str
    enabled: bool
    market: str
    source_type: str
    collection_method: str
    priority: str
    poll_interval_minutes: int
    health: str
    adapter_available: bool
    last_run_at: datetime | None
    last_run_status: str | None
    items_received: int
    items_new: int
    items_duplicate: int
    items_rejected: int
    last_error: str | None


class SourceRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    source: str
    run_id: int
    status: str
    items_received: int
    items_new: int
    items_duplicate: int
    items_rejected: int
    error: str | None
