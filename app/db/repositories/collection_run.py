from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CollectionRun


class CollectionRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start(self, *, source_id: int) -> CollectionRun:
        run = CollectionRun(source_id=source_id)
        self.session.add(run)
        await self.session.flush()
        return run

    async def finish(
        self,
        run: CollectionRun,
        *,
        status: str,
        fetched_count: int,
        new_count: int,
        duplicate_count: int = 0,
        rejected_count: int = 0,
        error: str | None = None,
    ) -> CollectionRun:
        run.finished_at = datetime.now(UTC)
        run.status = status
        run.fetched_count = fetched_count
        run.new_count = new_count
        run.duplicate_count = duplicate_count
        run.rejected_count = rejected_count
        run.error = error
        await self.session.flush()
        return run
