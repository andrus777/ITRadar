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
            select(ranked, Source.code)
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
                started_at=row.started_at,
                finished_at=row.finished_at,
                error=row.error,
            )
            for row in rows
        ]
