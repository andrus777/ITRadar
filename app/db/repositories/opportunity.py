from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Opportunity


class OpportunityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, opportunity_id: int) -> Opportunity | None:
        return await self.session.get(Opportunity, opportunity_id)

    async def add_or_get(self, **values: Any) -> Opportunity:
        opportunity, _ = await self.add_or_get_with_created(**values)
        return opportunity

    async def add_or_get_with_created(self, **values: Any) -> tuple[Opportunity, bool]:
        statement = (
            insert(Opportunity)
            .values(**values)
            .on_conflict_do_nothing(constraint="uq_opportunities_source_external")
            .returning(Opportunity)
        )
        opportunity = (await self.session.scalars(statement)).first()
        if opportunity is not None:
            return opportunity, True

        query = select(Opportunity).where(
            Opportunity.source_id == values["source_id"],
            Opportunity.external_id == values["external_id"],
        )
        return (await self.session.scalars(query)).one(), False
