import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.collectors.base import CollectorAdapter
from app.models import Opportunity
from app.schemas import CollectedItem, NormalizedOpportunity
from app.services import CollectorService

pytestmark = pytest.mark.integration


class StaticCollector(CollectorAdapter):
    source_name = "Static Test Source"
    base_url = "https://source.test"

    def __init__(
        self,
        *,
        source_code: str,
        external_id: str,
        title: str,
        description: str,
        url: str,
        budget_text: str,
    ) -> None:
        self._source_code = source_code
        self.item = CollectedItem(
            external_id=external_id,
            url=url,
            payload={
                "title": title,
                "description": description,
                "budget_text": budget_text,
            },
        )

    @property
    def source_code(self) -> str:
        return self._source_code

    async def fetch(self) -> list[CollectedItem]:
        return [self.item]

    def normalize(self, item: CollectedItem) -> NormalizedOpportunity:
        return NormalizedOpportunity(
            external_id=item.external_id,
            title=str(item.payload["title"]),
            description=str(item.payload["description"]),
            url=item.url,
            budget_text=str(item.payload["budget_text"]),
            published_at=datetime(2026, 9, 1, tzinfo=UTC),
            fetched_at=item.fetched_at,
            fingerprint="0" * 64,
        )


@pytest.mark.asyncio
async def test_cross_source_deduplication_is_conservative() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    collectors = [
        StaticCollector(
            source_code="dedupe-a",
            external_id="a-1",
            title="Python API integration",
            description="<p>Build a CRM integration with Python and FastAPI.</p>",
            url="https://www.example.test/orders/42/?utm_source=feed",
            budget_text="100–300 тыс. ₽",
        ),
        StaticCollector(
            source_code="dedupe-b",
            external_id="b-1",
            title=" Python API integration ",
            description="Build a CRM integration with Python and FastAPI.",
            url="https://example.test/orders/42",
            budget_text="100-300 тыс руб.",
        ),
        StaticCollector(
            source_code="dedupe-c",
            external_id="c-1",
            title="Python API integration",
            description="Build a CRM integration with Python and FastAPI.",
            url="https://mirror.test/project/987",
            budget_text="от 450 000 ₽",
        ),
        StaticCollector(
            source_code="dedupe-d",
            external_id="d-1",
            title="Python API integration",
            description="Create an internal warehouse inventory service.",
            url="https://another.test/orders/7",
            budget_text="договорная",
        ),
        StaticCollector(
            source_code="dedupe-e",
            external_id="e-1",
            title="Python API integration.",
            description="Build a CRM integration with Python and FastAPI!",
            url="https://near-duplicate.test/project/42",
            budget_text="100–300 тыс. ₽",
        ),
    ]

    try:
        async with engine.connect() as connection, connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)
            service = CollectorService(session)
            for collector in collectors:
                run = await service.run(collector)
                assert run.status == "success"

            opportunities = (
                await session.scalars(
                    select(Opportunity)
                    .where(
                        Opportunity.external_id.in_(["a-1", "b-1", "c-1", "d-1", "e-1"])
                    )
                    .order_by(Opportunity.external_id)
                )
            ).all()
            canonical, same_url, changed_budget, same_title_only, near_duplicate = opportunities

            assert canonical.duplicate_of_id is None
            assert same_url.duplicate_of_id == canonical.id
            assert same_url.content_hash == canonical.content_hash
            assert changed_budget.duplicate_of_id == canonical.id
            assert changed_budget.content_hash != canonical.content_hash
            assert changed_budget.fingerprint == canonical.fingerprint
            assert changed_budget.budget_from == 450_000
            assert same_title_only.duplicate_of_id is None
            assert same_title_only.budget_negotiable is True
            assert near_duplicate.content_hash != canonical.content_hash
            assert near_duplicate.fingerprint != canonical.fingerprint
            assert near_duplicate.duplicate_of_id == canonical.id

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
