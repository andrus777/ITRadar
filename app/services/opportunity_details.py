from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.opportunity_details import OpportunityDetailsRepository
from app.schemas.opportunity_details import OpportunityDetails, OpportunityUserStatus


class OpportunityDetailsService:
    def __init__(self, session: AsyncSession, *, profile_id: int | None) -> None:
        self.repository = OpportunityDetailsRepository(session)
        self.profile_id = profile_id

    async def get(self, opportunity_id: int) -> OpportunityDetails | None:
        row = await self.repository.get(opportunity_id, profile_id=self.profile_id)
        if row is None:
            return None
        reasons = [
            str(reason.get("message"))
            for reason in (row.matching_reasons or [])
            if reason.get("message")
        ]
        return OpportunityDetails(
            opportunity_id=row.opportunity_id,
            title=row.title,
            description=row.description,
            source=row.source,
            source_url=row.source_url,
            published_at=row.published_at,
            deadline_at=row.deadline_at,
            budget=row.budget,
            category=row.category,
            technologies=row.technologies,
            customer=row.customer,
            opportunity_type=row.opportunity_type,
            market=row.market,
            score=row.score,
            matching_reasons=reasons,
            user_status=row.user_status,
            ai_summary=row.ai_summary,
            ai_category=row.ai_category,
            ai_technologies=row.ai_technologies or [],
            complexity=row.complexity,
            commercial_score=row.commercial_score,
            risk_flags=row.risk_flags or [],
            budget_comment=row.budget_comment,
        )

    async def set_user_status(
        self, opportunity_id: int, status: OpportunityUserStatus
    ) -> None:
        if self.profile_id is None:
            raise ValueError("developer profile is not configured")
        await self.repository.set_user_status(
            opportunity_id,
            profile_id=self.profile_id,
            status=status,
        )
