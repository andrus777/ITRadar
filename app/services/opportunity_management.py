from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.opportunity_management import OpportunityManagementRepository
from app.schemas.opportunity_management import (
    OpportunityFilters,
    OpportunityListItem,
    OpportunityListPage,
)


class OpportunityManagementService:
    def __init__(self, session: AsyncSession, *, profile_id: int | None) -> None:
        self.repository = OpportunityManagementRepository(session)
        self.profile_id = profile_id

    async def search(self, filters: OpportunityFilters) -> OpportunityListPage:
        rows, total = await self.repository.search(filters, profile_id=self.profile_id)
        total_pages = max(1, ceil(total / filters.page_size))
        return OpportunityListPage(
            items=[
                OpportunityListItem(
                    opportunity_id=row.opportunity_id,
                    score=row.score,
                    title=row.title,
                    source=row.source,
                    source_code=row.source_code,
                    opportunity_type=row.opportunity_type,
                    market=row.market,
                    category=row.category,
                    technologies=row.technologies,
                    budget=row.budget,
                    published_at=row.published_at,
                    status=row.status,
                )
                for row in rows
            ],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=total_pages,
        )

    async def filter_values(self) -> tuple[list[tuple[str, str]], list[str]]:
        return await self.repository.filter_values()
