from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.analytics import AnalyticsRepository
from app.schemas.analytics import AnalyticsDay, AnalyticsPoint, AnalyticsSnapshot


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = AnalyticsRepository(session)

    async def snapshot(self, days: int = 30) -> AnalyticsSnapshot:
        if days not in (7, 30, 90):
            raise ValueError("analytics period must be 7, 30 or 90 days")
        by_day = await self.repository.opportunities_by_day(days)
        sources = await self.repository.sources(days)
        categories = await self.repository.categories(days)
        technologies = await self.repository.technologies(days)
        return AnalyticsSnapshot(
            days=days,
            opportunities_by_day=[AnalyticsDay(day=row[0].date(), count=row[1]) for row in by_day],
            sources=[AnalyticsPoint(label=row.label, count=row.count) for row in sources],
            categories=[AnalyticsPoint(label=row.label, count=row.count) for row in categories],
            technologies=[AnalyticsPoint(label=row.label, count=row.count) for row in technologies],
            loaded_at=datetime.now(UTC),
        )
