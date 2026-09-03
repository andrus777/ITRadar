from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Match, UserProfile
from app.schemas import DeveloperProfile, MatchResult, UserProfileCreate


class UserProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, profile: UserProfileCreate) -> UserProfile:
        values = profile.model_dump()
        for field in ("technologies", "categories", "exclude_keywords"):
            values[field] = self._normalized_terms(values[field])
        values["technology_weights"] = self._normalized_weights(values["technology_weights"])
        user_profile = UserProfile(**values)
        self.session.add(user_profile)
        await self.session.flush()
        return user_profile

    async def get_by_name(self, name: str) -> UserProfile | None:
        return await self.session.scalar(select(UserProfile).where(UserProfile.name == name))

    async def get(self, profile_id: int) -> UserProfile | None:
        return await self.session.get(UserProfile, profile_id)

    async def first(self) -> UserProfile | None:
        return await self.session.scalar(select(UserProfile).order_by(UserProfile.id).limit(1))

    async def update(self, profile: UserProfile, data: DeveloperProfile) -> UserProfile:
        profile.name = data.name.strip()
        profile.technology_weights = self._normalized_weights(data.technology_weights)
        profile.technologies = sorted(profile.technology_weights)
        profile.categories = self._normalized_terms(data.categories)
        profile.min_budget = data.min_budget
        profile.max_budget = data.max_budget
        profile.exclude_keywords = self._normalized_terms(data.exclude_keywords)
        await self.session.flush()
        return profile

    @staticmethod
    def _normalized_terms(values: list[str]) -> list[str]:
        return sorted({value.strip().casefold() for value in values if value.strip()})

    @staticmethod
    def _normalized_weights(values: dict[str, int]) -> dict[str, int]:
        return {
            key.strip().casefold(): weight for key, weight in sorted(values.items()) if key.strip()
        }


class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self, *, user_profile_id: int, opportunity_id: int, result: MatchResult
    ) -> Match:
        values = {
            "user_profile_id": user_profile_id,
            "opportunity_id": opportunity_id,
            "score": result.score,
            "reasons": [reason.model_dump() for reason in result.reasons],
        }
        statement = (
            insert(Match)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_matches_profile_opportunity",
                set_={
                    "score": result.score,
                    "reasons": values["reasons"],
                    "matched_at": func.clock_timestamp(),
                    "updated_at": func.clock_timestamp(),
                },
            )
            .returning(Match)
            .execution_options(populate_existing=True)
        )
        return (await self.session.scalars(statement)).one()
