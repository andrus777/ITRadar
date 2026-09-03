import json
import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.collectors import JobicyCollector
from app.services import CollectorService

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parents[1] / "fixtures" / "jobicy_response.json"


@pytest.mark.asyncio
async def test_bad_jobicy_card_does_not_stop_pipeline() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    engine = create_async_engine(database_url)

    try:
        async with (
            httpx.AsyncClient(transport=transport) as client,
            engine.connect() as connection,
            connection.begin() as transaction,
        ):
            session = AsyncSession(bind=connection, expire_on_commit=False)
            collector = JobicyCollector(count=3, client=client)
            collector.source_code = f"jobicy-{uuid4().hex}"

            run = await CollectorService(session).run(collector)

            assert run.status == "partial_failed"
            assert run.fetched_count == 3
            assert run.new_count == 2
            assert run.duplicate_count == 0
            assert run.rejected_count == 1
            assert "900003" in (run.error or "")

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
