from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.collectors import FreelanceRuCollector

FIXTURE = Path(__file__).parents[1] / "fixtures" / "freelance_ru_tasks.html"


@pytest.mark.asyncio
async def test_freelance_ru_parses_only_target_categories() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=html))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = FreelanceRuCollector(client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[0])

    assert [item.external_id for item in items] == ["9435", "9386"]
    assert normalized.title == "Исправить старый код сайта"
    assert normalized.description == "Нужно обновить PHP-код и подключение к базе данных."
    assert normalized.source_category == "Веб-разработка и IT"
    assert normalized.budget_text == "20 000 ₽ / заказ"
    assert normalized.published_at is not None
    assert normalized.opportunity_type == "freelance"
    assert normalized.market == "ru"
    assert normalized.url == "https://freelance.ru/task/view/9435"


@pytest.mark.asyncio
async def test_freelance_ru_allows_missing_optional_description() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=html))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = FreelanceRuCollector(client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[1])

    assert normalized.description is None
    assert normalized.budget_text == "Обсуждается индивидуально"
    assert normalized.source_category == "Искусственный интеллект"


def test_freelance_ru_relative_publication_time_is_deterministic() -> None:
    fetched_at = datetime(2026, 9, 3, 12, tzinfo=UTC)

    published_at = FreelanceRuCollector._published_at("2 часа назад", fetched_at)

    assert published_at == datetime(2026, 9, 3, 10, tzinfo=UTC)
