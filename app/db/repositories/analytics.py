from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Opportunity, Source


@dataclass(frozen=True, slots=True)
class CountRow:
    label: str
    count: int


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _since(self, days: int) -> datetime:
        return datetime.now(UTC) - timedelta(days=days)

    async def opportunities_by_day(self, days: int) -> list[tuple[datetime, int]]:
        day = func.date_trunc("day", Opportunity.fetched_at)
        query = (
            select(day, func.count(Opportunity.id))
            .where(
                Opportunity.fetched_at >= self._since(days), Opportunity.duplicate_of_id.is_(None)
            )
            .group_by(day)
            .order_by(day)
        )
        return [(row[0], row[1]) for row in (await self.session.execute(query)).all()]

    async def sources(self, days: int, limit: int = 10) -> list[CountRow]:
        query = (
            select(Source.name, func.count(Opportunity.id).label("total"))
            .join(Opportunity, Opportunity.source_id == Source.id)
            .where(
                Opportunity.fetched_at >= self._since(days), Opportunity.duplicate_of_id.is_(None)
            )
            .group_by(Source.name)
            .order_by(func.count(Opportunity.id).desc(), Source.name)
            .limit(limit)
        )
        return [CountRow(row[0], row[1]) for row in (await self.session.execute(query)).all()]

    async def categories(self, days: int, limit: int = 10) -> list[CountRow]:
        label = func.coalesce(func.nullif(Opportunity.category, ""), "other")
        query = (
            select(label, func.count(Opportunity.id).label("total"))
            .where(
                Opportunity.fetched_at >= self._since(days), Opportunity.duplicate_of_id.is_(None)
            )
            .group_by(label)
            .order_by(func.count(Opportunity.id).desc(), label)
            .limit(limit)
        )
        return [CountRow(row[0], row[1]) for row in (await self.session.execute(query)).all()]

    async def technologies(self, days: int, limit: int = 10) -> list[CountRow]:
        technology = func.jsonb_array_elements_text(Opportunity.technologies).table_valued("value")
        query = (
            select(technology.c.value, func.count().label("total"))
            .select_from(Opportunity)
            .join(technology, true())
            .where(
                Opportunity.fetched_at >= self._since(days), Opportunity.duplicate_of_id.is_(None)
            )
            .group_by(technology.c.value)
            .order_by(func.count().desc(), technology.c.value)
            .limit(limit)
        )
        return [CountRow(row[0], row[1]) for row in (await self.session.execute(query)).all()]
