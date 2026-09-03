from typing import Protocol

from app.db.session import async_session_factory
from app.schemas import DeveloperProfile
from app.services.developer_profile import DeveloperProfileService
from app.settings import Settings, get_settings


class DeveloperProfileProvider(Protocol):
    async def load(self) -> DeveloperProfile: ...

    async def save(self, profile: DeveloperProfile) -> DeveloperProfile: ...


class LocalDeveloperProfileProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _service(self, session) -> DeveloperProfileService:
        return DeveloperProfileService(
            session, profile_id=self.settings.telegram_default_profile_id
        )

    async def load(self) -> DeveloperProfile:
        async with async_session_factory() as session:
            profile = await self._service(session).get_or_create()
            await session.commit()
            return profile

    async def save(self, profile: DeveloperProfile) -> DeveloperProfile:
        async with async_session_factory() as session:
            updated = await self._service(session).save(profile)
            await session.commit()
            return updated
