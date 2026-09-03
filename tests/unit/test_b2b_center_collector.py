from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.collectors import B2BCenterCollector, ProcurementCollectorAdapter

FIXTURE = Path(__file__).parents[1] / "fixtures" / "b2b_center_tenders.html"


@pytest.mark.asyncio
async def test_b2b_center_parses_public_procurement_fields() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=html))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = B2BCenterCollector(client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[0])

    assert isinstance(collector, ProcurementCollectorAdapter)
    assert [item.external_id for item in items] == ["4581001", "57446"]
    assert normalized.title == "Разработка CRM-системы и интеграция по API"
    assert normalized.procurement_number == "4581001"
    assert normalized.procurement_method == "Запрос предложений"
    assert normalized.customer_name == "АО «Тестовый заказчик»"
    assert normalized.customer_type == "business"
    assert normalized.source_category == "Разработка программного обеспечения"
    assert normalized.published_at == datetime(2026, 9, 2, 7, 28, tzinfo=UTC)
    assert normalized.deadline_at == datetime(2026, 9, 8, 7, 0, tzinfo=UTC)
    assert normalized.documentation_url == normalized.url
    assert normalized.url == "https://www.b2b-center.ru/market/razrabotka-crm/tender-4581001/"
    assert normalized.opportunity_type == "tender"
    assert normalized.market == "ru"


@pytest.mark.asyncio
async def test_b2b_center_allows_missing_optional_fields() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=html))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = B2BCenterCollector(client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[1])

    assert normalized.customer_name is None
    assert normalized.published_at is None
    assert normalized.deadline_at is None
    assert normalized.budget_from is None
