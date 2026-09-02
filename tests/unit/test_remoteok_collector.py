import json
from pathlib import Path

import httpx
import pytest

from app.collectors import RemoteOKCollector

FIXTURE = Path(__file__).parents[1] / "fixtures" / "remoteok_response.json"


@pytest.mark.asyncio
async def test_remoteok_parses_public_json_and_skips_legal_metadata() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = RemoteOKCollector(count=10, client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[0])

    assert len(items) == 2
    assert normalized.title == "Python API Engineer"
    assert normalized.customer_name == "Example Software"
    assert normalized.budget_text == "80000-120000 USD"
    assert normalized.published_at is not None


@pytest.mark.asyncio
async def test_remoteok_treats_zero_salary_as_missing() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    async with httpx.AsyncClient(transport=transport) as client:
        collector = RemoteOKCollector(count=10, client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[1])

    assert normalized.budget_from is None
    assert normalized.budget_to is None
    assert normalized.budget_text is None
