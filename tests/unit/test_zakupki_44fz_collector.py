from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.collectors import ProcurementCollectorAdapter, Zakupki44FZCollector

FIXTURE = Path(__file__).parents[1] / "fixtures" / "zakupki_44fz_results.html"


@pytest.mark.asyncio
async def test_zakupki_44fz_parses_public_search_results() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text=html)

    transport = httpx.MockTransport(respond)
    async with httpx.AsyncClient(transport=transport) as client:
        collector = Zakupki44FZCollector(queries=("программное обеспечение",), client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[0])

    assert isinstance(collector, ProcurementCollectorAdapter)
    assert [item.external_id for item in items] == [
        "0173100000126000123",
        "0373100000226000456",
    ]
    assert requests[0].url.params["fz44"] == "on"
    assert "fz223" not in requests[0].url.params
    assert normalized.title == "Разработка государственной информационной системы"
    assert normalized.budget_text == "12 500 000,00 ₽"
    assert normalized.customer_name == "Федеральное государственное учреждение"
    assert normalized.customer_type == "government"
    assert normalized.procurement_number == "0173100000126000123"
    assert normalized.procurement_method == "Электронный аукцион"
    assert normalized.source_category == "44-ФЗ"
    assert normalized.location == "Москва"
    assert normalized.published_at == datetime(2026, 9, 9, 11, 30, tzinfo=UTC)
    assert normalized.deadline_at == datetime(2026, 9, 18, 6, 0, tzinfo=UTC)
    assert normalized.documentation_url == normalized.url


@pytest.mark.asyncio
async def test_zakupki_44fz_deduplicates_queries_and_allows_optional_fields() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=html))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = Zakupki44FZCollector(queries=("ПО", "ИТ"), client=client)
        items = await collector.fetch()

    assert len(items) == 2
    normalized = collector.normalize(items[1])
    assert normalized.budget_text is None
    assert normalized.customer_name is None
    assert normalized.deadline_at is None


@pytest.mark.asyncio
async def test_zakupki_44fz_keeps_successful_query_when_another_fails() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    calls = 0

    def respond(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503 if calls == 1 else 200, text=html)

    transport = httpx.MockTransport(respond)
    async with httpx.AsyncClient(transport=transport) as client:
        collector = Zakupki44FZCollector(queries=("ошибка", "ПО"), client=client, retry_attempts=1)
        items = await collector.fetch()

    assert len(items) == 2
