from pathlib import Path

import httpx
import pytest

from app.collectors import WeWorkRemotelyCollector

FIXTURE = Path(__file__).parents[1] / "fixtures" / "weworkremotely_response.xml"


@pytest.mark.asyncio
async def test_weworkremotely_parses_public_rss() -> None:
    content = FIXTURE.read_bytes()
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=content))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = WeWorkRemotelyCollector(count=10, client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[0])

    assert len(items) == 2
    assert normalized.title == "Python API Engineer"
    assert normalized.customer_name == "Example Software"
    assert normalized.location == "Anywhere in the World"
    assert normalized.published_at is not None


@pytest.mark.asyncio
async def test_weworkremotely_allows_missing_optional_fields() -> None:
    content = FIXTURE.read_bytes()
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=content))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = WeWorkRemotelyCollector(count=10, client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[1])

    assert normalized.location is None
    assert normalized.published_at is None
    assert normalized.budget_text is None
