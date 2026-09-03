from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.registry import available_collectors
from app.db.session import async_session_factory
from app.schemas.source_management import SourceRunResult, SourceSummary
from app.services.source_management import SourceManagementService
from app.settings import Settings, get_settings


class SourceProvider(Protocol):
    async def list_sources(self) -> list[SourceSummary]: ...

    async def set_enabled(self, code: str, enabled: bool) -> SourceSummary: ...

    async def run_source(self, code: str) -> SourceRunResult: ...


class LocalSourceProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _service(self, session: AsyncSession) -> SourceManagementService:
        return SourceManagementService(
            session,
            collectors=available_collectors(self.settings),
        )

    async def list_sources(self) -> list[SourceSummary]:
        async with async_session_factory() as session:
            items = await self._service(session).list_sources()
            await session.commit()
            return items

    async def set_enabled(self, code: str, enabled: bool) -> SourceSummary:
        async with async_session_factory() as session:
            item = await self._service(session).set_enabled(code, enabled)
            await session.commit()
            return item

    async def run_source(self, code: str) -> SourceRunResult:
        async with async_session_factory() as session:
            try:
                result = await self._service(session).run_source(code)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
