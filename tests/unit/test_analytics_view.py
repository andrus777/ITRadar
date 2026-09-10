import os
from datetime import UTC, date, datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from app.desktop.app import create_application
from app.desktop.views.analytics_view import AnalyticsView
from app.schemas.analytics import AnalyticsDay, AnalyticsPoint, AnalyticsSnapshot


class FakeAnalyticsProvider:
    async def load(self, days: int) -> AnalyticsSnapshot:
        return AnalyticsSnapshot(
            days=days,
            opportunities_by_day=[AnalyticsDay(day=date(2026, 9, 10), count=4)],
            sources=[AnalyticsPoint(label="FL.ru", count=3)],
            categories=[AnalyticsPoint(label="backend", count=2)],
            technologies=[AnalyticsPoint(label="Python", count=2)],
            loaded_at=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_analytics_view_renders_all_dimensions() -> None:
    create_application(["it-radar-analytics-test"])
    view = AnalyticsView(FakeAnalyticsProvider())

    await view.refresh()

    assert view.daily_table.item(0, 1).text() == "4"
    assert view.source_table.item(0, 0).text() == "FL.ru"
    assert view.category_table.item(0, 0).text() == "backend"
    assert view.technology_table.item(0, 0).text() == "Python"
