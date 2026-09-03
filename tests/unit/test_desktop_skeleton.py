import os
from datetime import UTC, datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from app.desktop.app import create_application
from app.desktop.main_window import NAVIGATION_ITEMS, MainWindow
from app.desktop.views import DashboardView
from app.schemas.dashboard import (
    DashboardMetric,
    DashboardOpportunity,
    DashboardSnapshot,
    DashboardSystemStatus,
)


class FakeDashboardProvider:
    async def load(self) -> DashboardSnapshot:
        return DashboardSnapshot(
            metrics=[DashboardMetric(key="new", label="Новые", value="3")],
            opportunities=[
                DashboardOpportunity(
                    opportunity_id=42,
                    score=94,
                    title="Telegram bot + CRM",
                    source="FL.ru",
                    budget="180–250 тыс. ₽",
                    opportunity_type="project",
                    published_at=datetime(2026, 9, 3, 10, 0, tzinfo=UTC),
                )
            ],
            statuses=[
                DashboardSystemStatus(
                    key="database", label="Database", state="ok", detail="connected"
                )
            ],
            loaded_at=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
        )


class FailingDashboardProvider:
    async def load(self) -> DashboardSnapshot:
        raise RuntimeError("postgresql+asyncpg://user:secret@localhost/database")


def test_desktop_application_metadata() -> None:
    application = create_application(["it-radar-desktop-test"])

    assert application.applicationName() == "IT Radar Desktop"
    assert application.organizationName() == "IT Radar"
    assert application.styleSheet()


def test_main_window_navigation_switches_workspace() -> None:
    create_application(["it-radar-desktop-test"])
    window = MainWindow()

    assert window.minimumWidth() == 1280
    assert window.minimumHeight() == 800
    assert window.navigation_list.count() == len(NAVIGATION_ITEMS)
    assert window.workspace.count() == len(NAVIGATION_ITEMS)
    assert window.workspace.currentWidget().objectName() == "dashboardView"

    window.navigation_list.setCurrentRow(5)

    assert window.workspace.currentWidget().objectName() == "telegramView"
    assert window.statusBar().currentMessage() == "Ready"


@pytest.mark.asyncio
async def test_dashboard_renders_snapshot_and_emits_selected_opportunity() -> None:
    create_application(["it-radar-desktop-test"])
    view = DashboardView(FakeDashboardProvider())
    selected: list[int] = []
    view.opportunity_activated.connect(selected.append)

    await view.refresh()
    view.opportunities_table.cellDoubleClicked.emit(0, 1)

    assert view.opportunities_table.rowCount() == 1
    assert view.opportunities_table.item(0, 0).text() == "94%"
    assert view.opportunities_table.item(0, 1).text() == "Telegram bot + CRM"
    assert selected == [42]
    assert view.refresh_button.isEnabled()


@pytest.mark.asyncio
async def test_dashboard_reports_database_failure_without_exposing_exception() -> None:
    create_application(["it-radar-desktop-test"])
    view = DashboardView(FailingDashboardProvider())

    await view.refresh()

    assert "недоступна" in view.feedback.text()
    assert "secret" not in view.feedback.text()
    assert view.refresh_button.isEnabled()
