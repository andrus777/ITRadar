from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors import CollectorAdapter
from app.collectors.registry import CollectorRegistration
from app.db.repositories import SourceRepository
from app.db.repositories.source_management import SourceManagementRepository
from app.schemas.source_management import SourceRunResult, SourceSummary
from app.services.collector import CollectorService


class SourceManagementService:
    """Manage collectors through Python services without exposing SQL or CLI to clients."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        collectors: dict[str, CollectorRegistration],
    ) -> None:
        self.session = session
        self.collectors = collectors
        self.sources = SourceRepository(session)
        self.repository = SourceManagementRepository(session)

    async def list_sources(self) -> list[SourceSummary]:
        await self._synchronize_sources()
        rows = await self.repository.list_with_latest_run()
        return [
            SourceSummary(
                source_id=row.source_id,
                code=row.code,
                name=row.name,
                base_url=row.base_url,
                enabled=row.enabled,
                market=row.market,
                source_type=row.source_type,
                collection_method=row.collection_method,
                priority=row.priority,
                poll_interval_minutes=row.poll_interval_minutes,
                health=row.health,
                adapter_available=row.code in self.collectors,
                last_run_at=row.last_run_at,
                last_run_status=row.last_run_status,
                items_received=row.items_received or 0,
                items_new=row.items_new or 0,
                items_duplicate=row.items_duplicate or 0,
                items_rejected=row.items_rejected or 0,
                last_error=row.last_error,
            )
            for row in rows
        ]

    async def set_enabled(self, code: str, enabled: bool) -> SourceSummary:
        await self._synchronize_sources()
        source = await self.sources.get_by_code(code)
        if source is None:
            raise LookupError(f"source {code} not found")
        await self.sources.set_enabled(source, enabled)
        summaries = await self.list_sources()
        return next(item for item in summaries if item.code == code)

    async def run_source(self, code: str) -> SourceRunResult:
        await self._synchronize_sources()
        source = await self.sources.get_by_code(code)
        registration = self.collectors.get(code)
        if source is None or registration is None:
            raise LookupError(f"collector {code} is not available")
        if not source.enabled:
            raise ValueError(f"source {code} is disabled")
        run = await CollectorService(self.session).run(registration.adapter)
        return SourceRunResult(
            source=code,
            run_id=run.id,
            status=run.status,
            items_received=run.fetched_count,
            items_new=run.new_count,
            items_duplicate=run.duplicate_count,
            items_rejected=run.rejected_count,
            error=run.error,
        )

    async def enabled_collectors(self) -> dict[str, CollectorAdapter]:
        await self._synchronize_sources()
        sources = {source.code: source for source in await self.sources.list_all()}
        return {
            code: registration.adapter
            for code, registration in self.collectors.items()
            if code in sources and sources[code].enabled
        }

    async def _synchronize_sources(self) -> None:
        for code, registration in self.collectors.items():
            adapter = registration.adapter
            source = await self.sources.get_by_code(code)
            metadata = {
                "name": adapter.source_name,
                "base_url": adapter.base_url,
                "source_type": adapter.source_type,
                "market": adapter.market,
                "priority": adapter.priority,
                "collection_method": adapter.collection_method,
                "poll_interval_minutes": adapter.poll_interval_minutes,
            }
            if source is None:
                await self.sources.create(
                    code=code,
                    enabled=registration.enabled_by_default,
                    **metadata,
                )
            else:
                await self.sources.update_metadata(source, **metadata)
