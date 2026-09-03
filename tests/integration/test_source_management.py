import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.collectors import FixtureCollector
from app.collectors.registry import CollectorRegistration
from app.services import PipelineReport, PipelineService, SourceManagementService

pytestmark = pytest.mark.integration
FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.mark.asyncio
async def test_source_management_sync_toggle_run_and_stats() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection, connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)
            collector = FixtureCollector(FIXTURES / "opportunities.json")
            collector.source_code = f"managed-{uuid4().hex}"
            collector.source_name = "Managed Fixture"
            service = SourceManagementService(
                session,
                collectors={
                    collector.source_code: CollectorRegistration(
                        enabled_by_default=False,
                        adapter=collector,
                    )
                },
            )

            initial = await service.list_sources()
            initial_source = next(item for item in initial if item.code == collector.source_code)
            assert initial_source.enabled is False
            assert initial_source.last_run_status is None

            enabled = await service.set_enabled(collector.source_code, True)
            result = await service.run_source(collector.source_code)
            after = await service.list_sources()
            managed_source = next(item for item in after if item.code == collector.source_code)

            assert enabled.enabled is True
            assert result.status == "partial_failed"
            assert result.items_received == 3
            assert result.items_new + result.items_duplicate == 2
            assert managed_source.health == "degraded"
            assert managed_source.last_run_status == "partial_failed"
            assert managed_source.items_new + managed_source.items_duplicate == 2
            assert managed_source.items_rejected == 1

            await service.set_enabled(collector.source_code, False)
            with pytest.raises(ValueError, match="disabled"):
                await service.run_source(collector.source_code)

            pipeline = PipelineService(
                async_sessionmaker(bind=connection, expire_on_commit=False),
                collectors={collector.source_code: collector},
                ai_provider=None,
                digest_sender=None,
                profile_id=1,
                prompt_version="v1",
                digest_min_score=70,
            )
            report = PipelineReport()
            await pipeline._collect(report)

            assert report.collection_statuses[collector.source_code] == "disabled"

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
