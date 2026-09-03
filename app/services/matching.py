from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import MatchRepository
from app.models import AIAnalysis, Match, Opportunity, UserProfile
from app.schemas import MatchReason, MatchResult


class MatchingEngine:
    """Deterministic profile matching; no provider or network calls are involved."""

    TECHNOLOGY_POINTS = 35
    CATEGORY_POINTS = 20
    BUDGET_POINTS = 25
    REMOTE_POINTS = 20

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.matches = MatchRepository(session) if session is not None else None

    def calculate(
        self,
        profile: UserProfile,
        opportunity: Opportunity,
        analysis: AIAnalysis | None = None,
    ) -> MatchResult:
        searchable_text = " ".join(
            filter(
                None,
                (
                    opportunity.title,
                    opportunity.description,
                    analysis.summary if analysis else None,
                ),
            )
        ).casefold()
        excluded = [word for word in profile.exclude_keywords if word.casefold() in searchable_text]
        if excluded:
            return MatchResult(
                score=0,
                reasons=[
                    MatchReason(
                        factor="blacklist",
                        matched=False,
                        points=0,
                        message=f"Исключающие слова найдены: {', '.join(sorted(excluded))}",
                    )
                ],
            )

        reasons = [
            self._technology_reason(profile, analysis),
            self._category_reason(profile, analysis),
            self._budget_reason(profile, opportunity),
            self._remote_reason(profile, opportunity),
        ]
        return MatchResult(score=sum(reason.points for reason in reasons), reasons=reasons)

    async def calculate_and_store(
        self,
        profile: UserProfile,
        opportunity: Opportunity,
        analysis: AIAnalysis | None = None,
    ) -> Match:
        if self.matches is None:
            raise RuntimeError("AsyncSession is required to store matches")
        result = self.calculate(profile, opportunity, analysis)
        return await self.matches.upsert(
            user_profile_id=profile.id, opportunity_id=opportunity.id, result=result
        )

    def _technology_reason(self, profile: UserProfile, analysis: AIAnalysis | None) -> MatchReason:
        weights = {
            item.casefold(): weight for item, weight in (profile.technology_weights or {}).items()
        }
        wanted = set(weights) or {item.casefold() for item in profile.technologies}
        actual = {item.casefold() for item in (analysis.technologies or [])} if analysis else set()
        common = sorted(wanted & actual)
        if not wanted:
            return MatchReason(
                factor="technologies",
                matched=True,
                points=self.TECHNOLOGY_POINTS,
                message="Ограничений по технологиям нет",
            )
        if common:
            points = (
                round(
                    self.TECHNOLOGY_POINTS
                    * sum(weights[item] for item in common)
                    / sum(weights.values())
                )
                if weights
                else self.TECHNOLOGY_POINTS
            )
            return MatchReason(
                factor="technologies",
                matched=True,
                points=points,
                message=f"Совпали технологии: {', '.join(common)}",
            )
        return MatchReason(
            factor="technologies", matched=False, points=0, message="Нужные технологии не найдены"
        )

    def _category_reason(self, profile: UserProfile, analysis: AIAnalysis | None) -> MatchReason:
        wanted = {item.casefold() for item in profile.categories}
        category = analysis.category.casefold() if analysis and analysis.category else None
        if not wanted:
            return MatchReason(
                factor="category",
                matched=True,
                points=self.CATEGORY_POINTS,
                message="Ограничений по категории нет",
            )
        if category in wanted:
            return MatchReason(
                factor="category",
                matched=True,
                points=self.CATEGORY_POINTS,
                message=f"Категория подходит: {category}",
            )
        return MatchReason(
            factor="category", matched=False, points=0, message="Категория не соответствует профилю"
        )

    def _budget_reason(self, profile: UserProfile, opportunity: Opportunity) -> MatchReason:
        if profile.min_budget is None and profile.max_budget is None:
            return MatchReason(
                factor="budget",
                matched=True,
                points=self.BUDGET_POINTS,
                message="Ограничений по бюджету нет",
            )
        lower = opportunity.budget_from
        upper = opportunity.budget_to
        if lower is None and upper is None:
            return MatchReason(
                factor="budget", matched=False, points=0, message="Бюджет заказа не указан"
            )
        overlaps = self._ranges_overlap(profile.min_budget, profile.max_budget, lower, upper)
        return MatchReason(
            factor="budget",
            matched=overlaps,
            points=self.BUDGET_POINTS if overlaps else 0,
            message="Бюджет пересекается с диапазоном профиля"
            if overlaps
            else "Бюджет вне диапазона профиля",
        )

    def _remote_reason(self, profile: UserProfile, opportunity: Opportunity) -> MatchReason:
        matches = not profile.remote_only or opportunity.remote is True
        return MatchReason(
            factor="remote",
            matched=matches,
            points=self.REMOTE_POINTS if matches else 0,
            message="Формат работы подходит"
            if matches
            else "Профиль допускает только удалённую работу",
        )

    @staticmethod
    def _ranges_overlap(
        wanted_min: Decimal | None,
        wanted_max: Decimal | None,
        actual_min: Decimal | None,
        actual_max: Decimal | None,
    ) -> bool:
        return (wanted_min is None or actual_max is None or actual_max >= wanted_min) and (
            wanted_max is None or actual_min is None or actual_min <= wanted_max
        )
