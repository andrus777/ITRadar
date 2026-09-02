from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import OpportunityBrowserRepository, OpportunityCardRow
from app.schemas import OpportunityCard, OpportunityPage, ProfileView


class OpportunityBrowserService:
    def __init__(self, session: AsyncSession, *, profile_id: int) -> None:
        self.repository = OpportunityBrowserRepository(session)
        self.profile_id = profile_id

    async def latest(self, page: int = 0) -> OpportunityPage:
        return await self._page(order="latest", page=page)

    async def top(self, page: int = 0) -> OpportunityPage:
        return await self._page(order="top", page=page)

    async def profile(self) -> ProfileView | None:
        profile = await self.repository.get_profile(self.profile_id)
        if profile is None:
            return None
        return ProfileView(
            name=profile.name,
            technologies=profile.technologies,
            categories=profile.categories,
            min_budget=self._amount(profile.min_budget),
            max_budget=self._amount(profile.max_budget),
            exclude_keywords=profile.exclude_keywords,
            remote_only=profile.remote_only,
        )

    async def _page(self, *, order: str, page: int) -> OpportunityPage:
        safe_page = max(page, 0)
        rows = await self.repository.list_cards(
            profile_id=self.profile_id,
            order=order,
            offset=safe_page,
            limit=2,
        )
        card = self.card_from_row(rows[0]) if rows else None
        return OpportunityPage(
            card=card,
            page=safe_page,
            has_previous=safe_page > 0,
            has_next=len(rows) > 1,
        )

    @staticmethod
    def card_from_row(row: OpportunityCardRow) -> OpportunityCard:
        reasons = [
            str(reason.get("message")) for reason in (row.reasons or []) if reason.get("message")
        ]
        return OpportunityCard(
            opportunity_id=row.opportunity_id,
            title=row.title,
            budget=row.budget_text,
            source_name=row.source_name,
            source_url=row.source_url,
            summary=row.summary,
            score=row.score,
            reasons=reasons,
            published_at=row.published_at,
        )

    @staticmethod
    def _amount(value: Decimal | None) -> str | None:
        return f"{value:g}" if value is not None else None
