from pathlib import Path

import pytest

from app.collectors import FixtureCollector

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.mark.asyncio
async def test_fixture_collector_reads_json_and_html() -> None:
    collector = FixtureCollector(
        FIXTURES / "opportunities.json",
        FIXTURES / "opportunities.html",
    )

    items = await collector.fetch()
    normalized = collector.normalize(items[0])

    assert len(items) == 4
    assert normalized.title == "Python API integration"
    assert normalized.currency == "RUB"
    assert items[-1].external_id == "html-1"
