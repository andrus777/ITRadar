from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Match, UserProfile
from app.schemas import MatchResult, UserProfileCreate


class UserProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, profile: UserProfileCreate) -> UserProfile:
        values = profile.model_dump()
        for field in ("technologies", "categories", "exclude_keywords"):
            values[field] = self._normalized_terms(values[field])
        user_profile = UserProfile(**values)
        self.session.add(user_profile)
        await self.session.flush()
        return user_profile

    @staticmethod
    def _normalized_terms(values: list[str]) -> list[str]:
        return sorted({value.strip().casefold() for value in values if value.strip()})


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
                set_={"score": result.score, "reasons": values["reasons"]},
            )
            .returning(Match)
        )
        return (await self.session.scalars(statement)).one()
