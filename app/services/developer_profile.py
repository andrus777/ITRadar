from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import UserProfileRepository
from app.schemas import DeveloperProfile, UserProfileCreate


class DeveloperProfileService:
    def __init__(self, session: AsyncSession, *, profile_id: int | None = None) -> None:
        self.repository = UserProfileRepository(session)
        self.profile_id = profile_id

    async def get_or_create(self) -> DeveloperProfile:
        profile = (
            await self.repository.get(self.profile_id)
            if self.profile_id is not None
            else await self.repository.first()
        )
        if profile is None:
            profile = await self.repository.create(UserProfileCreate(name="Desktop profile"))
        return self._to_schema(profile)

    async def save(self, data: DeveloperProfile) -> DeveloperProfile:
        profile = await self.repository.get(data.profile_id)
        if profile is None:
            raise LookupError(f"profile {data.profile_id} not found")
        return self._to_schema(await self.repository.update(profile, data))

    @staticmethod
    def _to_schema(profile) -> DeveloperProfile:
        weights = dict(profile.technology_weights or {})
        for technology in profile.technologies:
            weights.setdefault(technology, 5)
        return DeveloperProfile(
            profile_id=profile.id,
            name=profile.name,
            technology_weights=weights,
            categories=profile.categories,
            min_budget=profile.min_budget,
            max_budget=profile.max_budget,
            exclude_keywords=profile.exclude_keywords,
        )
