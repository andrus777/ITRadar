import os
from datetime import UTC, datetime
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from app.desktop.app import create_application
from app.desktop.views import TelegramView
from app.schemas import TelegramActionResult, TelegramConfiguration, TelegramOverview


class FakeTelegramProvider:
    def __init__(self) -> None:
        self.configuration = TelegramConfiguration(
            enabled=True,
            chat_id=123456789,
            min_score=75,
            min_budget=Decimal("100000"),
            max_items=10,
            include_international=False,
            include_types=["project", "tender"],
        )

    async def overview(self) -> TelegramOverview:
        return TelegramOverview(
            configured=True,
            token_mask="12345...ABCD",
            configuration=self.configuration,
            last_digest_at=datetime(2026, 9, 3, 8, 0, tzinfo=UTC),
            next_digest_at=datetime(2026, 9, 3, 20, 0, tzinfo=UTC),
        )

    async def save(self, configuration: TelegramConfiguration) -> TelegramOverview:
        self.configuration = configuration
        return await self.overview()

    def run_action(self, action, configuration, progress, cancel_event):
        raise AssertionError("background execution is covered separately")


@pytest.mark.asyncio
async def test_telegram_view_loads_saves_and_previews_without_exposing_token() -> None:
    create_application(["it-radar-telegram-test"])
    provider = FakeTelegramProvider()
    view = TelegramView(provider)

    await view.load()
    assert view.bot_status.text() == "Настроено"
    assert view.token_mask.text() == "12345...ABCD"
    assert view.chat_id.text() == "123456789"
    assert view.configuration().include_types == ["project", "tender"]

    view.min_score.setValue(80)
    view.max_items.setValue(5)
    await view.save()
    assert provider.configuration.min_score == 80
    assert provider.configuration.max_items == 5

    view._action_complete(
        TelegramActionResult(message="Preview: 1 opportunities", preview=["<b>Order</b>"])
    )
    assert "Order" in view.preview.toPlainText()
