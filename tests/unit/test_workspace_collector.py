from pathlib import Path

import httpx
import pytest

from app.collectors import WorkspaceCollector

FIXTURE = Path(__file__).parents[1] / "fixtures" / "workspace_tenders.html"


@pytest.mark.asyncio
async def test_workspace_parses_public_tenders_and_required_fields() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=html))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = WorkspaceCollector(client=client, feed_urls=("https://workspace.ru/tenders/",))
        items = await collector.fetch()

    normalized = collector.normalize(items[0])

    assert [item.external_id for item in items] == ["1544", "3453"]
    assert normalized.title == "Мобильное приложение для сети студий красоты"
    assert normalized.budget_text == "1 000 000 - 1 500 000 ₽"
    assert normalized.published_at is not None
    assert normalized.deadline_at is not None
    assert normalized.opportunity_type == "tender"
    assert normalized.market == "ru"
    assert normalized.url.endswith("-1544/")


@pytest.mark.asyncio
async def test_workspace_missing_optional_description_is_allowed() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=html))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = WorkspaceCollector(client=client, feed_urls=("https://workspace.ru/tenders/",))
        items = await collector.fetch()

    normalized = collector.normalize(items[1])

    assert normalized.description is None
    assert normalized.budget_text == "до 100 000 ₽"


@pytest.mark.asyncio
async def test_workspace_rejects_anti_bot_page_without_bypass() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, text="Для продолжения подтвердите, что вы не робот")
    )
    async with httpx.AsyncClient(transport=transport) as client:
        collector = WorkspaceCollector(client=client, feed_urls=("https://workspace.ru/tenders/",))
        with pytest.raises(RuntimeError, match="anti-bot"):
            await collector.fetch()
