from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CollectionRun, Source
from app.schemas import CollectionRunStatus


class OperationsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ping(self) -> None:
        await self.session.execute(select(1))

    async def latest_collection_runs(self) -> list[CollectionRunStatus]:
        ranked = select(
            CollectionRun.id.label("run_id"),
            CollectionRun.source_id,
            CollectionRun.status,
            CollectionRun.fetched_count,
            CollectionRun.new_count,
            CollectionRun.duplicate_count,
            CollectionRun.rejected_count,
            CollectionRun.started_at,
            CollectionRun.finished_at,
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
                ranked,
                Source.code,
                Source.health_status,
                Source.last_success_at,
                Source.last_error_at,
            )
            .join(Source, Source.id == ranked.c.source_id)
            .where(ranked.c.position == 1)
            .order_by(Source.code)
        )
        rows = (await self.session.execute(query)).all()
        return [
            CollectionRunStatus(
                run_id=row.run_id,
                source=row.code,
                status=row.status,
                fetched_count=row.fetched_count,
                new_count=row.new_count,
                duplicate_count=row.duplicate_count,
                rejected_count=row.rejected_count,
                items_received=row.fetched_count,
                items_new=row.new_count,
                items_duplicate=row.duplicate_count,
                items_rejected=row.rejected_count,
                health=row.health_status,
                last_success_at=row.last_success_at,
                last_error_at=row.last_error_at,
                started_at=row.started_at,
                finished_at=row.finished_at,
                error=row.error,
            )
            for row in rows
        ]
