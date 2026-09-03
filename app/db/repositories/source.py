from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Source


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_code(self, code: str) -> Source | None:
        return await self.session.scalar(select(Source).where(Source.code == code))

    async def create(
        self,
        *,
        code: str,
        name: str,
        base_url: str,
        source_type: str = "api",
        market: str = "unknown",
        priority: str = "P2",
        collection_method: str = "api",
        poll_interval_minutes: int = 60,
    ) -> Source:
        source = Source(
            code=code,
            name=name,
            base_url=base_url,
            source_type=source_type,
            market=market,
            priority=priority,
            collection_method=collection_method,
            poll_interval_minutes=poll_interval_minutes,
        )
        self.session.add(source)
        await self.session.flush()
        return source

    async def update_metadata(self, source: Source, **values: object) -> Source:
        for field, value in values.items():
            setattr(source, field, value)
        await self.session.flush()
        return source

    async def record_run_result(self, source: Source, *, status: str, error: str | None) -> Source:
        now = datetime.now(UTC)
        if status == "success":
            source.health_status = "healthy"
            source.last_success_at = now
            source.last_error = None
        elif status == "partial_failed":
            source.health_status = "degraded"
            source.last_success_at = now
            source.last_error_at = now
            source.last_error = error
        else:
            source.health_status = "unhealthy"
            source.last_error_at = now
            source.last_error = error
        await self.session.flush()
        return source
