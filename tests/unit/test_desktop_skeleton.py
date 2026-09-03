import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from app.desktop.app import create_application
from app.desktop.main_window import NAVIGATION_ITEMS, MainWindow


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
