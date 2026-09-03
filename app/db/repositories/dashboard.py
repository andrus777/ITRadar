from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import case, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIAnalysis, CollectionRun, Match, Opportunity, Source


@dataclass(frozen=True, slots=True)
class DashboardStats:
    new_count: int
    matched_count: int
    healthy_sources: int
    total_sources: int
    degraded_sources: int
    unhealthy_sources: int
    error_count: int
    average_budget: Decimal | None
    ai_queue_count: int


@dataclass(frozen=True, slots=True)
class DashboardOpportunityRow:
    opportunity_id: int
    score: int
    title: str
    source: str
    budget: str | None
    opportunity_type: str
    published_at: datetime | None


class DashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def statistics(self, *, profile_id: int | None) -> DashboardStats:
        since = datetime.now(UTC) - timedelta(hours=24)
        canonical = (Opportunity.duplicate_of_id.is_(None), Opportunity.status == "active")
        budget_midpoint = case(
            (
                Opportunity.budget_from.is_not(None) & Opportunity.budget_to.is_not(None),
                (Opportunity.budget_from + Opportunity.budget_to) / 2,
            ),
            else_=func.coalesce(Opportunity.budget_from, Opportunity.budget_to),
        )
        successful_current_analysis = exists(
            select(AIAnalysis.id).where(
                AIAnalysis.opportunity_id == Opportunity.id,
                AIAnalysis.status == "success",
                AIAnalysis.input_hash == Opportunity.content_hash,
            )
        )

        new_count = await self.session.scalar(
            select(func.count(Opportunity.id)).where(*canonical, Opportunity.fetched_at >= since)
        )
        source_counts = (
            await self.session.execute(
                select(
                    func.count(Source.id),
                    func.count(Source.id).filter(Source.health_status == "healthy"),
                    func.count(Source.id).filter(Source.health_status == "degraded"),
                    func.count(Source.id).filter(Source.health_status == "unhealthy"),
                ).where(Source.enabled.is_(True))
            )
        ).one()
        error_count = await self.session.scalar(
            select(func.count(CollectionRun.id)).where(
                CollectionRun.started_at >= since,
                CollectionRun.status.in_(("failed", "partial_failed")),
            )
        )
        average_budget = await self.session.scalar(
            select(func.avg(budget_midpoint)).where(*canonical, budget_midpoint.is_not(None))
        )
        ai_queue_count = await self.session.scalar(
            select(func.count(Opportunity.id)).where(*canonical, ~successful_current_analysis)
        )

        matched_count = 0
        if profile_id is not None:
            matched_count = (
                await self.session.scalar(
                    select(func.count(Match.id))
                    .join(Opportunity, Opportunity.id == Match.opportunity_id)
                    .where(*canonical, Match.user_profile_id == profile_id, Match.score >= 80)
                )
                or 0
            )

        return DashboardStats(
            new_count=new_count or 0,
            matched_count=matched_count,
            total_sources=source_counts[0] or 0,
            healthy_sources=source_counts[1] or 0,
            degraded_sources=source_counts[2] or 0,
            unhealthy_sources=source_counts[3] or 0,
            error_count=error_count or 0,
            average_budget=average_budget,
            ai_queue_count=ai_queue_count or 0,
        )

    async def top_opportunities(
        self, *, profile_id: int | None, limit: int = 5
    ) -> list[DashboardOpportunityRow]:
        if profile_id is None:
            return []
        query = (
            select(
                Opportunity.id,
                Match.score,
                Opportunity.title,
                Source.name,
                Opportunity.budget_text,
                Opportunity.opportunity_type,
                Opportunity.published_at,
            )
            .join(Source, Source.id == Opportunity.source_id)
            .join(
                Match,
                (Match.opportunity_id == Opportunity.id)
                & (Match.user_profile_id == profile_id),
            )
            .where(Opportunity.duplicate_of_id.is_(None), Opportunity.status == "active")
            .order_by(Match.score.desc(), Opportunity.published_at.desc().nullslast())
            .limit(limit)
        )
        return [DashboardOpportunityRow(*row) for row in (await self.session.execute(query)).all()]
