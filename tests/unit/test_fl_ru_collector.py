from pathlib import Path

import httpx
import pytest

from app.collectors import FLRuCollector

FIXTURE = Path(__file__).parents[1] / "fixtures" / "fl_ru_response.xml"


@pytest.mark.asyncio
async def test_fl_ru_parses_official_rss_and_filters_categories() -> None:
    content = FIXTURE.read_bytes()
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=content))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = FLRuCollector(client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[0])

    assert [item.external_id for item in items] == ["5520499", "5520496"]
    assert normalized.title == "Интеграция Озон доставки на сайт"
    assert normalized.budget_text == "10 000 ₽"
    assert normalized.market == "ru"
    assert normalized.opportunity_type == "freelance"
    assert normalized.published_at is not None


@pytest.mark.asyncio
async def test_fl_ru_deduplicates_category_feed_intersections() -> None:
    content = FIXTURE.read_bytes()
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=content))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = FLRuCollector(
            client=client,
            feed_urls=("https://www.fl.ru/rss/all.xml", "https://www.fl.ru/rss/all.xml"),
        )
        items = await collector.fetch()

    assert [item.external_id for item in items] == ["5520499", "5520496"]


@pytest.mark.asyncio
async def test_fl_ru_allows_missing_optional_fields() -> None:
    content = FIXTURE.read_bytes()
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=content))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = FLRuCollector(client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[1])

    assert normalized.budget_text is None
    assert normalized.published_at is None
