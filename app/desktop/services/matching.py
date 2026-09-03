import asyncio
from collections.abc import Callable
from threading import Event
from typing import Protocol

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import async_session_factory
from app.schemas import (
    MatchDistribution,
    MatchingRecalculationProgress,
    MatchingRecalculationResult,
)
from app.services import MatchingRecalculationService
from app.settings import Settings, get_settings


class MatchingProvider(Protocol):
    async def distribution(self, profile_id: int) -> MatchDistribution: ...

    def recalculate(
        self,
        profile_id: int,
        progress: Callable[[MatchingRecalculationProgress], None],
        cancel_event: Event,
    ) -> MatchingRecalculationResult: ...


class LocalMatchingProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def distribution(self, profile_id: int) -> MatchDistribution:
        async with async_session_factory() as session:
            return await MatchingRecalculationService(session).distribution(profile_id)

    def recalculate(
        self,
        profile_id: int,
        progress: Callable[[MatchingRecalculationProgress], None],
        cancel_event: Event,
    ) -> MatchingRecalculationResult:
        return asyncio.run(self._recalculate(profile_id, progress, cancel_event))

    async def _recalculate(
        self,
        profile_id: int,
        progress: Callable[[MatchingRecalculationProgress], None],
        cancel_event: Event,
    ) -> MatchingRecalculationResult:
        engine = create_async_engine(self.settings.database_url, pool_pre_ping=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                try:
                    result = await MatchingRecalculationService(session).recalculate(
                        profile_id,
                        progress=progress,
                        cancelled=cancel_event.is_set,
                    )
                    await session.commit()
                    return result
                except Exception:
                    await session.rollback()
                    raise
        finally:
            await engine.dispose()
