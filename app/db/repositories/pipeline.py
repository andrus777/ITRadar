from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.opportunity_browser import OpportunityCardRow
from app.models import AIAnalysis, Match, Opportunity, Source, UserProfile


@dataclass(frozen=True, slots=True)
class PendingDigest:
    match: Match
    card: OpportunityCardRow


class PipelineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_profile(self, profile_id: int) -> UserProfile | None:
        return await self.session.get(UserProfile, profile_id)

    async def active_opportunities(self) -> list[Opportunity]:
        query = (
            select(Opportunity)
            .where(Opportunity.status == "active", Opportunity.duplicate_of_id.is_(None))
            .order_by(Opportunity.id)
        )
        return list(await self.session.scalars(query))

    async def latest_successful_analysis(self, opportunity_id: int) -> AIAnalysis | None:
        query = (
            select(AIAnalysis)
            .where(
                AIAnalysis.opportunity_id == opportunity_id,
                AIAnalysis.status == "success",
            )
            .order_by(AIAnalysis.analyzed_at.desc(), AIAnalysis.id.desc())
            .limit(1)
        )
        return (await self.session.scalars(query)).first()

    async def pending_digest(
        self,
        *,
        profile_id: int,
        min_score: int,
        limit: int,
        include_international: bool = False,
    ) -> list[PendingDigest]:
        latest_analysis_id = (
            select(AIAnalysis.id)
            .where(
                AIAnalysis.opportunity_id == Opportunity.id,
                AIAnalysis.status == "success",
            )
            .order_by(AIAnalysis.analyzed_at.desc(), AIAnalysis.id.desc())
            .limit(1)
            .correlate(Opportunity)
            .scalar_subquery()
        )
        query = (
            select(
                Match,
                Opportunity.id,
                Opportunity.title,
                Opportunity.budget_text,
                Source.name,
                Opportunity.url,
                AIAnalysis.summary,
                Match.score,
                Match.reasons,
                Opportunity.published_at,
            )
            .join(Opportunity, Opportunity.id == Match.opportunity_id)
            .join(Source, Source.id == Opportunity.source_id)
            .outerjoin(AIAnalysis, AIAnalysis.id == latest_analysis_id)
            .where(
                Match.user_profile_id == profile_id,
                Match.score >= min_score,
                Match.notified_at.is_(None),
                Opportunity.status == "active",
                Opportunity.duplicate_of_id.is_(None),
            )
            .order_by(Match.score.desc(), Match.id)
            .limit(limit)
            .with_for_update(of=Match, skip_locked=True)
        )
        if not include_international:
            query = query.where(Opportunity.market != "international")
        rows = (await self.session.execute(query)).all()
        return [PendingDigest(match=row[0], card=OpportunityCardRow(*row[1:])) for row in rows]
