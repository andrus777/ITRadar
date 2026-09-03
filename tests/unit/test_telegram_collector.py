from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from app.collectors import (
    TelegramChannelCollector,
    TelegramChannelConfig,
    parse_telegram_whitelist,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "telegram_channel.html"


@pytest.mark.asyncio
async def test_telegram_collector_reads_only_whitelisted_public_channel() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, text=FIXTURE.read_text(encoding="utf-8"))
    )
    channel = TelegramChannelConfig(username="@job_for_bots", category="freelance")
    async with httpx.AsyncClient(transport=transport) as client:
        collector = TelegramChannelCollector(channel=channel, client=client)
        items = await collector.fetch()

    normalized = collector.normalize(items[0])

    assert [item.external_id for item in items] == ["101", "102"]
    assert normalized.title == "Нужен Telegram-бот для CRM"
    assert normalized.description is not None
    assert normalized.budget_text == "150 000 ₽"
    assert normalized.published_at == datetime(2026, 9, 3, 8, 12, 51, tzinfo=UTC)
    assert normalized.url == "https://t.me/job_for_bots/101"
    assert normalized.opportunity_type == "freelance"
    assert normalized.market == "ru"


def test_telegram_whitelist_validates_channel_and_category() -> None:
    channels = parse_telegram_whitelist(
        '[{"username":"job_for_bots","enabled":true,"category":"projects"}]'
    )

    assert channels[0].username == "job_for_bots"
    assert channels[0].category == "projects"

    with pytest.raises(ValidationError):
        TelegramChannelConfig(username="https://t.me/channel", category="projects")
