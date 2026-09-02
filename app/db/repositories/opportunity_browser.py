from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIAnalysis, Match, Opportunity, Source, UserProfile


@dataclass(frozen=True, slots=True)
class OpportunityCardRow:
    opportunity_id: int
    title: str
    budget_text: str | None
    source_name: str
    source_url: str
    summary: str | None
    score: int | None
    reasons: list[dict[str, object]] | None
    published_at: datetime | None


class OpportunityBrowserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_profile(self, profile_id: int) -> UserProfile | None:
        return await self.session.get(UserProfile, profile_id)

    async def list_cards(
        self,
        *,
        profile_id: int,
        order: str,
        offset: int,
        limit: int,
    ) -> list[OpportunityCardRow]:
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
        columns = (
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
        query = (
            select(*columns)
            .join(Source, Source.id == Opportunity.source_id)
            .outerjoin(AIAnalysis, AIAnalysis.id == latest_analysis_id)
            .where(Opportunity.duplicate_of_id.is_(None), Opportunity.status == "active")
        )
        if order == "top":
            query = query.join(
                Match,
                (Match.opportunity_id == Opportunity.id) & (Match.user_profile_id == profile_id),
            ).order_by(Match.score.desc(), Opportunity.published_at.desc().nullslast())
        elif order == "latest":
            query = query.outerjoin(
                Match,
                (Match.opportunity_id == Opportunity.id) & (Match.user_profile_id == profile_id),
            ).order_by(
                Opportunity.published_at.desc().nullslast(),
                Opportunity.fetched_at.desc(),
            )
        else:
            raise ValueError(f"unsupported card order: {order}")

        rows = (await self.session.execute(query.offset(offset).limit(limit))).all()
        return [OpportunityCardRow(*row) for row in rows]
