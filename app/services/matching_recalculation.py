from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import MatchRepository, PipelineRepository, UserProfileRepository
from app.schemas import (
    MatchDistribution,
    MatchingRecalculationProgress,
    MatchingRecalculationResult,
)
from app.services.matching import MatchingEngine


class MatchingRecalculationService:
    """Rebuild deterministic matches and summarize the current score distribution."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.profiles = UserProfileRepository(session)
        self.pipeline = PipelineRepository(session)
        self.matches = MatchRepository(session)

    async def distribution(self, profile_id: int) -> MatchDistribution:
        return self._distribution(await self.matches.scores(user_profile_id=profile_id))

    async def recalculate(
        self,
        profile_id: int,
        *,
        progress: Callable[[MatchingRecalculationProgress], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> MatchingRecalculationResult:
        profile = await self.profiles.get(profile_id)
        if profile is None:
            raise LookupError(f"profile {profile_id} not found")
        candidates = []
        for opportunity in await self.pipeline.active_opportunities():
            analysis = await self.pipeline.latest_successful_analysis(opportunity.id)
            if analysis is None or analysis.is_opportunity is not False:
                candidates.append((opportunity, analysis))
        total = len(candidates)
        processed = 0
        matching = MatchingEngine(self.session)
        for opportunity, analysis in candidates:
            if cancelled is not None and cancelled():
                break
            await matching.calculate_and_store(profile, opportunity, analysis)
            processed += 1
            if progress is not None:
                progress(MatchingRecalculationProgress(processed=processed, total=total))
        await self.session.flush()
        return MatchingRecalculationResult(
            processed=processed,
            total=total,
            cancelled=processed < total and cancelled is not None and cancelled(),
            distribution=await self.distribution(profile_id),
        )

    @staticmethod
    def _distribution(scores: list[int]) -> MatchDistribution:
        return MatchDistribution(
            excellent=sum(score >= 90 for score in scores),
            strong=sum(80 <= score < 90 for score in scores),
            possible=sum(70 <= score < 80 for score in scores),
            low=sum(score < 70 for score in scores),
        )
