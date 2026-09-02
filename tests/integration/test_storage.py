import os
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models import Opportunity
from app.services.opportunity_storage import OpportunityStorageService

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_store_source_raw_and_idempotent_opportunity() -> None:
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
                code=f"fixture-{suffix}",
                name="Fixture Source",
                base_url="https://example.test",
            )
            raw = await storage.store_raw(
                source_id=source.id,
                external_id="job-1",
                url="https://example.test/jobs/1",
                payload={"title": "Python API"},
                content_hash="a" * 64,
            )
            first = await storage.store_opportunity(
                source_id=source.id,
                external_id="job-1",
                title="Python API",
                description="Build an integration",
                url="https://example.test/jobs/1",
                fingerprint="b" * 64,
            )
            repeated = await storage.store_opportunity(
                source_id=source.id,
                external_id="job-1",
                title="Duplicate title is ignored",
                description=None,
                url="https://example.test/jobs/1",
                fingerprint="c" * 64,
            )
            loaded = await storage.opportunities.get(first.id)
            count = await session.scalar(
                select(func.count()).select_from(Opportunity).where(
                    Opportunity.source_id == source.id,
                    Opportunity.external_id == "job-1",
                )
            )

            assert raw.payload == {"title": "Python API"}
            assert loaded is not None
            assert loaded.title == "Python API"
            assert repeated.id == first.id
            assert count == 1

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
