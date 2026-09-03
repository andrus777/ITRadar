from typing import Protocol

from app.db.session import async_session_factory
from app.schemas.dashboard import DashboardSnapshot
from app.services.dashboard import DashboardService
from app.settings import Settings, get_settings


class DashboardProvider(Protocol):
    async def load(self) -> DashboardSnapshot: ...


class LocalDashboardProvider:
    """Use application services directly while keeping the view transport-agnostic."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def load(self) -> DashboardSnapshot:
        async with async_session_factory() as session:
            service = DashboardService(session)
            return await service.snapshot(
                profile_id=self.settings.telegram_default_profile_id,
                ai_enabled=self.settings.ai_api_key is not None,
                telegram_enabled=self.settings.telegram_bot_token is not None,
            )
