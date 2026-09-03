import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.collectors import B2BCenterCollector
from app.models import Opportunity, Source
from app.services import CollectorService

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parents[1] / "fixtures" / "b2b_center_tenders.html"


@pytest.mark.asyncio
async def test_b2b_center_pipeline_persists_procurement_fields() -> None:
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
                collector = B2BCenterCollector(client=client)
                collector.source_code = f"b2b-center-{uuid4().hex}"
                run = await CollectorService(session).run(collector)

            source = await session.get(Source, run.source_id)
            opportunity = await session.scalar(
                select(Opportunity).where(
                    Opportunity.source_id == run.source_id,
                    Opportunity.external_id == "4581001",
                )
            )

            assert run.status == "success"
            assert run.fetched_count == 2
            assert run.new_count == 2
            assert source is not None
            assert source.source_type == "procurement"
            assert source.priority == "P1"
            assert source.market == "ru"
            assert opportunity is not None
            assert opportunity.procurement_number == "4581001"
            assert opportunity.procurement_method == "Запрос предложений"
            assert opportunity.customer_name == "АО «Тестовый заказчик»"
            assert opportunity.customer_type == "business"
            assert opportunity.category == "crm"
            assert opportunity.deadline_at is not None
            assert opportunity.documentation_url == opportunity.url

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
