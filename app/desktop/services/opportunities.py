from typing import Protocol

from app.db.session import async_session_factory
from app.schemas.opportunity_management import OpportunityFilters, OpportunityListPage
from app.services.opportunity_management import OpportunityManagementService
from app.settings import Settings, get_settings


class OpportunityProvider(Protocol):
    async def search(self, filters: OpportunityFilters) -> OpportunityListPage: ...

    async def filter_values(self) -> tuple[list[tuple[str, str]], list[str]]: ...


class LocalOpportunityProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def search(self, filters: OpportunityFilters) -> OpportunityListPage:
        async with async_session_factory() as session:
            return await OpportunityManagementService(
                session,
                profile_id=self.settings.telegram_default_profile_id,
            ).search(filters)

    async def filter_values(self) -> tuple[list[tuple[str, str]], list[str]]:
        async with async_session_factory() as session:
            return await OpportunityManagementService(
                session,
                profile_id=self.settings.telegram_default_profile_id,
            ).filter_values()
