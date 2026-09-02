import os
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.main import app
from app.services import CollectorService
from tests.integration.test_scheduled_pipeline import FailingCollector

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_ready_reports_database_and_latest_source_run() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    suffix = uuid4().hex
    collector = FailingCollector(Path(__file__))
    collector.source_code = f"ready-{suffix}"
    try:
        async with session_factory() as session:
            run = await CollectorService(session).run(collector)
            await session.commit()

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/ready")

            assert response.status_code == 200
            payload = response.json()
            assert payload["database"] == "up"
            source_run = next(
                item
                for item in payload["collection_runs"]
                if item["source"] == collector.source_code
            )
            assert source_run["run_id"] == run.id
            assert source_run["status"] == "failed"
            assert source_run["error"] == "source unavailable"

    finally:
        await engine.dispose()
