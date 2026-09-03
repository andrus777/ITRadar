import os
from datetime import UTC, datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from app.desktop.app import create_application
from app.desktop.views import SourcesView
from app.schemas.source_management import SourceRunResult, SourceSummary


class FakeSourceProvider:
    def __init__(self) -> None:
        self.source = SourceSummary(
            source_id=1,
            code="fl_ru",
            name="FL.ru",
            base_url="https://www.fl.ru",
            enabled=True,
            market="ru",
            source_type="rss",
            collection_method="rss",
            priority="P0",
            poll_interval_minutes=60,
            health="healthy",
            adapter_available=True,
            last_run_at=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
            last_run_status="success",
            items_received=20,
            items_new=4,
            items_duplicate=2,
            items_rejected=1,
            last_error=None,
        )
        self.runs = 0

    async def list_sources(self) -> list[SourceSummary]:
        return [self.source]

    async def set_enabled(self, code: str, enabled: bool) -> SourceSummary:
        assert code == "fl_ru"
        self.source = self.source.model_copy(update={"enabled": enabled})
        return self.source

    async def run_source(self, code: str) -> SourceRunResult:
        assert code == "fl_ru"
        self.runs += 1
        return SourceRunResult(
            source=code,
            run_id=2,
            status="success",
            items_received=10,
            items_new=3,
            items_duplicate=1,
            items_rejected=0,
            error=None,
        )


@pytest.mark.asyncio
async def test_sources_view_loads_stats_toggles_and_runs_source() -> None:
    create_application(["it-radar-desktop-test"])
    provider = FakeSourceProvider()
    view = SourcesView(provider)

    await view.load()

    assert view.table.rowCount() == 1
    assert view.table.item(0, 1).text() == "FL.ru"
    assert view.table.item(0, 7).text() == "4"
    assert view.run_button.isEnabled()

    await view.run_selected()
    assert provider.runs == 1
    assert "получено 10" in view.feedback.text()

    await view.toggle_selected()
    assert provider.source.enabled is False
    assert view.toggle_button.text() == "Enable"
    assert not view.run_button.isEnabled()
