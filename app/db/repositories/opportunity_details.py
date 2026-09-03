from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIAnalysis, Match, Opportunity, OpportunityUserState, Source
from app.schemas.opportunity_details import OpportunityUserStatus


@dataclass(frozen=True, slots=True)
class OpportunityDetailsRow:
    opportunity_id: int
    title: str
    description: str | None
    source: str
    source_url: str
    published_at: datetime | None
    deadline_at: datetime | None
    budget: str | None
    category: str
    technologies: list[str]
    customer: str | None
    opportunity_type: str
    market: str
    score: int | None
    matching_reasons: list[dict[str, object]] | None
    user_status: str
    ai_summary: str | None
    ai_category: str | None
    ai_technologies: list[str] | None
    complexity: int | None
    commercial_score: int | None
    risk_flags: list[str] | None
    budget_comment: str | None


class OpportunityDetailsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self, opportunity_id: int, *, profile_id: int | None
    ) -> OpportunityDetailsRow | None:
        opportunity_row = (
            await self.session.execute(
                select(Opportunity, Source.name)
                .join(Source, Source.id == Opportunity.source_id)
                .where(Opportunity.id == opportunity_id)
            )
        ).one_or_none()
        if opportunity_row is None:
            return None
        opportunity, source_name = opportunity_row
        analysis = await self.session.scalar(
            select(AIAnalysis)
            .where(AIAnalysis.opportunity_id == opportunity_id, AIAnalysis.status == "success")
            .order_by(AIAnalysis.analyzed_at.desc(), AIAnalysis.id.desc())
            .limit(1)
        )
        match = None
        user_state = None
        if profile_id is not None:
            match = await self.session.scalar(
                select(Match).where(
                    Match.opportunity_id == opportunity_id,
                    Match.user_profile_id == profile_id,
                )
            )
            user_state = await self.session.scalar(
                select(OpportunityUserState).where(
                    OpportunityUserState.opportunity_id == opportunity_id,
                    OpportunityUserState.user_profile_id == profile_id,
                )
            )
        return OpportunityDetailsRow(
            opportunity_id=opportunity.id,
            title=opportunity.title,
            description=opportunity.description,
            source=source_name,
            source_url=opportunity.url,
            published_at=opportunity.published_at,
            deadline_at=opportunity.deadline_at,
            budget=opportunity.budget_text,
            category=opportunity.category,
            technologies=opportunity.technologies,
            customer=opportunity.customer_name,
            opportunity_type=opportunity.opportunity_type,
            market=opportunity.market,
            score=match.score if match else None,
            matching_reasons=match.reasons if match else None,
            user_status=user_state.status if user_state else "new",
            ai_summary=analysis.summary if analysis else None,
            ai_category=analysis.category if analysis else None,
            ai_technologies=analysis.technologies if analysis else None,
            complexity=analysis.complexity if analysis else None,
            commercial_score=analysis.commercial_score if analysis else None,
            risk_flags=analysis.risk_flags if analysis else None,
            budget_comment=analysis.budget_comment if analysis else None,
        )

    async def set_user_status(
        self,
        opportunity_id: int,
        *,
        profile_id: int,
        status: OpportunityUserStatus,
    ) -> None:
        statement = (
            insert(OpportunityUserState)
            .values(
                opportunity_id=opportunity_id,
                user_profile_id=profile_id,
                status=status,
            )
            .on_conflict_do_update(
                constraint="uq_opportunity_user_states_profile_opportunity",
                set_={"status": status, "updated_at": func.clock_timestamp()},
            )
        )
        await self.session.execute(statement)
