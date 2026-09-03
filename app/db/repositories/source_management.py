from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CollectionRun, Source


@dataclass(frozen=True, slots=True)
class SourceSummaryRow:
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
    last_run_at: datetime | None
    last_run_status: str | None
    items_received: int | None
    items_new: int | None
    items_duplicate: int | None
    items_rejected: int | None
    last_error: str | None


class SourceManagementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_with_latest_run(self) -> list[SourceSummaryRow]:
        ranked_runs = select(
            CollectionRun.source_id,
            CollectionRun.started_at,
            CollectionRun.status,
            CollectionRun.fetched_count,
            CollectionRun.new_count,
            CollectionRun.duplicate_count,
            CollectionRun.rejected_count,
            CollectionRun.error,
            func.row_number()
            .over(
                partition_by=CollectionRun.source_id,
                order_by=CollectionRun.started_at.desc(),
            )
            .label("position"),
        ).subquery()
        query = (
            select(
                Source.id,
                Source.code,
                Source.name,
                Source.base_url,
                Source.enabled,
                Source.market,
                Source.source_type,
                Source.collection_method,
                Source.priority,
                Source.poll_interval_minutes,
                Source.health_status,
                ranked_runs.c.started_at,
                ranked_runs.c.status,
                ranked_runs.c.fetched_count,
                ranked_runs.c.new_count,
                ranked_runs.c.duplicate_count,
                ranked_runs.c.rejected_count,
                ranked_runs.c.error,
            )
            .outerjoin(
                ranked_runs,
                and_(ranked_runs.c.source_id == Source.id, ranked_runs.c.position == 1),
            )
            .order_by(Source.priority, Source.name)
        )
        return [SourceSummaryRow(*row) for row in (await self.session.execute(query)).all()]
