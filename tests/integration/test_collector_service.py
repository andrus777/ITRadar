import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.collectors import FixtureCollector
from app.models import CollectionRun, Opportunity, RawItem
from app.services.collector import CollectorService

pytestmark = pytest.mark.integration
FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.mark.asyncio
async def test_collector_is_idempotent_and_records_partial_errors() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    suffix = uuid4().hex

    try:
        async with engine.connect() as connection, connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)
            collector = FixtureCollector(FIXTURES / "opportunities.json")
            collector.source_code = f"fixture-{suffix}"
            service = CollectorService(session)

            first = await service.run(collector)
            second = await service.run(collector)

            raw_count = await session.scalar(select(func.count()).select_from(RawItem))
            opportunity_count = await session.scalar(
                select(func.count()).select_from(Opportunity)
            )
            runs = (
                await session.scalars(
                    select(CollectionRun)
                    .where(CollectionRun.source_id == first.source_id)
                    .order_by(CollectionRun.id)
                )
            ).all()

            assert raw_count == 3
            assert opportunity_count == 2
            assert first.status == "partial_failed"
            assert first.fetched_count == 3
            assert first.new_count == 2
            assert "json-broken" in (first.error or "")
            assert second.status == "partial_failed"
            assert second.new_count == 0
            assert len(runs) == 2
            assert all(run.finished_at is not None for run in runs)

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
