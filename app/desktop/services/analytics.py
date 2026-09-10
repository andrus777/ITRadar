from typing import Protocol

from app.db.session import async_session_factory
from app.schemas.analytics import AnalyticsSnapshot
from app.services.analytics import AnalyticsService


class AnalyticsProvider(Protocol):
    async def load(self, days: int) -> AnalyticsSnapshot: ...


class LocalAnalyticsProvider:
    async def load(self, days: int) -> AnalyticsSnapshot:
        async with async_session_factory() as session:
            return await AnalyticsService(session).snapshot(days)
