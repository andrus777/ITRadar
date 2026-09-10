import os
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.services.analytics import AnalyticsService
from app.services.opportunity_storage import OpportunityStorageService

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_analytics_aggregates_canonical_opportunities() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")
    engine = create_async_engine(database_url)
    suffix = uuid4().hex
    try:
        async with engine.connect() as connection, connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)
            storage = OpportunityStorageService(session)
            source = await storage.ensure_source(
                code=f"analytics-{suffix}",
                name=f"Analytics {suffix}",
                base_url="https://example.test",
            )
            opportunity = await storage.store_opportunity(
                source_id=source.id,
                external_id="one",
                title="Python backend",
                description="API",
                url=f"https://example.test/{suffix}",
                fingerprint=suffix.ljust(64, "0")[:64],
            )
            opportunity.category = f"backend-{suffix}"
            opportunity.technologies = [f"Python-{suffix}"]
            await session.flush()

            snapshot = await AnalyticsService(session).snapshot(7)

            assert any(row.label == source.name and row.count == 1 for row in snapshot.sources)
            assert any(row.label == opportunity.category for row in snapshot.categories)
            assert any(row.label == opportunity.technologies[0] for row in snapshot.technologies)
            assert sum(row.count for row in snapshot.opportunities_by_day) >= 1
            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
