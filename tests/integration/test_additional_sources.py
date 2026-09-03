import json
import os
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.collectors import RemoteOKCollector, WeWorkRemotelyCollector
from app.models import Opportunity
from app.services import CollectorService

pytestmark = pytest.mark.integration
FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.mark.asyncio
async def test_real_source_adapters_share_generic_cross_source_deduplication() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    remoteok_payload = json.loads((FIXTURES / "remoteok_response.json").read_text(encoding="utf-8"))
    wwr_payload = (FIXTURES / "weworkremotely_response.xml").read_bytes()
    remoteok_transport = httpx.MockTransport(lambda _: httpx.Response(200, json=remoteok_payload))
    wwr_transport = httpx.MockTransport(lambda _: httpx.Response(200, content=wwr_payload))
    engine = create_async_engine(database_url)

    try:
        async with (
            httpx.AsyncClient(transport=remoteok_transport) as remoteok_client,
            httpx.AsyncClient(transport=wwr_transport) as wwr_client,
            engine.connect() as connection,
            connection.begin() as transaction,
        ):
            session = AsyncSession(bind=connection, expire_on_commit=False)
            service = CollectorService(session)

            remoteok_run = await service.run(RemoteOKCollector(count=2, client=remoteok_client))
            wwr_run = await service.run(WeWorkRemotelyCollector(count=2, client=wwr_client))
            remoteok_job = await session.scalar(
                select(Opportunity).where(
                    Opportunity.source_id == remoteok_run.source_id,
                    Opportunity.external_id == "910001",
                )
            )
            wwr_job = await session.scalar(
                select(Opportunity).where(
                    Opportunity.source_id == wwr_run.source_id,
                    Opportunity.external_id
                    == "https://weworkremotely.com/remote-jobs/example-software-python-api-engineer",
                )
            )

            assert remoteok_run.status == "success"
            assert remoteok_run.fetched_count == 2
            assert remoteok_run.new_count == 2
            assert remoteok_run.duplicate_count == 0
            assert wwr_run.status == "success"
            assert wwr_run.fetched_count == 2
            assert wwr_run.new_count == 1
            assert wwr_run.duplicate_count == 1
            assert wwr_run.rejected_count == 0
            assert remoteok_job is not None
            assert wwr_job is not None
            assert wwr_job.duplicate_of_id == remoteok_job.id

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
