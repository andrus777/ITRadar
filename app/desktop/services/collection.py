import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.collectors.registry import available_collectors
from app.schemas.source_management import SourceRunResult
from app.services.source_management import SourceManagementService
from app.settings import Settings, get_settings


@dataclass(frozen=True, slots=True)
class CollectionProgress:
    source: str
    position: int
    total: int
    state: str
    result: SourceRunResult | None = None


@dataclass(frozen=True, slots=True)
class CollectionBatchResult:
    completed: int
    total: int
    cancelled: bool


class LocalCollectionRunner:
    """Invoke collector services directly in a worker-owned asyncio/DB context."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run(
        self,
        source_codes: list[str],
        progress: Callable[[CollectionProgress], None],
        cancel_event: Event,
    ) -> CollectionBatchResult:
        return asyncio.run(self._run(source_codes, progress, cancel_event))

    async def _run(
        self,
        source_codes: list[str],
        progress: Callable[[CollectionProgress], None],
        cancel_event: Event,
    ) -> CollectionBatchResult:
        engine = create_async_engine(self.settings.database_url, pool_pre_ping=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        registrations = available_collectors(self.settings)
        completed = 0
        try:
            for position, code in enumerate(dict.fromkeys(source_codes), start=1):
                if cancel_event.is_set():
                    break
                progress(CollectionProgress(code, position, len(source_codes), "running"))
                async with factory() as session:
                    service = SourceManagementService(session, collectors=registrations)
                    try:
                        result = await service.run_source(code)
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        result = SourceRunResult(
                            source=code,
                            run_id=0,
                            status="failed",
                            items_received=0,
                            items_new=0,
                            items_duplicate=0,
                            items_rejected=0,
                            error="Collector failed",
                        )
                completed += 1
                progress(
                    CollectionProgress(code, position, len(source_codes), result.status, result)
                )
        finally:
            await engine.dispose()
        return CollectionBatchResult(completed, len(source_codes), cancel_event.is_set())
