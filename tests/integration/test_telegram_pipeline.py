import os
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.collectors import TelegramChannelCollector, TelegramChannelConfig
from app.models import Opportunity, Source
from app.services import CollectorService

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parents[1] / "fixtures" / "telegram_channel.html"


@pytest.mark.asyncio
async def test_telegram_whitelist_pipeline_persists_message_candidates() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, text=FIXTURE.read_text(encoding="utf-8"))
    )
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection, connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)
            async with httpx.AsyncClient(transport=transport) as client:
                collector = TelegramChannelCollector(
                    channel=TelegramChannelConfig(username="job_for_bots", category="freelance"),
                    client=client,
                )
                run = await CollectorService(session).run(collector)

            source = await session.get(Source, run.source_id)
            opportunity = await session.scalar(
                select(Opportunity).where(
                    Opportunity.source_id == run.source_id,
                    Opportunity.external_id == "101",
                )
            )

            assert run.status == "success"
            assert run.fetched_count == 2
            assert source is not None
            assert source.source_type == "telegram"
            assert source.collection_method == "telegram"
            assert source.priority == "P1"
            assert opportunity is not None
            assert opportunity.budget_from == 150_000
            assert opportunity.currency == "RUB"
            assert opportunity.category == "telegram"
            assert opportunity.technologies == ["postgresql", "telegram"]

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
