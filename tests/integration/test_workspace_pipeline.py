import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.collectors import WorkspaceCollector
from app.models import Opportunity, Source
from app.services import CollectorService

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parents[1] / "fixtures" / "workspace_tenders.html"


@pytest.mark.asyncio
async def test_workspace_fixture_pipeline_persists_required_tender_fields() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    html = FIXTURE.read_text(encoding="utf-8")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=html))
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection, connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)
            async with httpx.AsyncClient(transport=transport) as client:
                collector = WorkspaceCollector(
                    client=client,
                    feed_urls=("https://workspace.ru/tenders/crm/",),
                )
                collector.source_code = f"workspace-{uuid4().hex}"
                run = await CollectorService(session).run(collector)

            source = await session.scalar(select(Source).where(Source.id == run.source_id))
            opportunity = await session.scalar(
                select(Opportunity)
                .where(Opportunity.source_id == run.source_id)
                .order_by(Opportunity.external_id)
            )

            assert run.status == "success"
            assert run.fetched_count == 2
            assert run.new_count == 2
            assert source is not None
            assert source.market == "ru"
            assert source.priority == "P0"
            assert source.collection_method == "html"
            assert opportunity is not None
            assert opportunity.budget_from is not None
            assert opportunity.currency == "RUB"
            assert opportunity.deadline_at is not None
            assert opportunity.opportunity_type == "tender"
            assert opportunity.url.startswith("https://workspace.ru/tenders/")

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
