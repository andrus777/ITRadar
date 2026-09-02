import json
from pathlib import Path

import httpx
import pytest

from app.collectors import JobicyCollector

FIXTURE = Path(__file__).parents[1] / "fixtures" / "jobicy_response.json"


def fixture_response() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_jobicy_parses_and_normalizes_public_api_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["count"] == "3"
        return httpx.Response(200, json=fixture_response())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        collector = JobicyCollector(count=3, client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[0])

    assert len(items) == 3
    assert normalized.external_id == "900001"
    assert normalized.title == "Python API Engineer"
    assert normalized.description == "Build async Python integrations. FastAPI PostgreSQL"
    assert normalized.published_at is not None
    assert normalized.budget_text == "80000-120000 USD yearly"
    assert normalized.url.startswith("https://jobicy.com/jobs/")


@pytest.mark.asyncio
async def test_jobicy_allows_missing_optional_salary_fields() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=fixture_response()))
    ) as client:
        collector = JobicyCollector(count=3, client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[1])

    assert normalized.budget_from is None
    assert normalized.budget_to is None
    assert normalized.currency is None
    assert normalized.budget_text is None
