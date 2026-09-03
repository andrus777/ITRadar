import asyncio
import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from app.desktop.main_window import MainWindow
from app.desktop.services import LocalDashboardProvider, LocalOpportunityProvider
from app.desktop.theme import DARK_THEME


def create_application(argv: Sequence[str] | None = None) -> QApplication:
    """Create or return the process-wide Qt application."""
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing

    application = QApplication(list(argv) if argv is not None else sys.argv)
    application.setApplicationName("IT Radar Desktop")
    application.setApplicationDisplayName("IT Radar")
    application.setOrganizationName("IT Radar")
    application.setStyle("Fusion")
    application.setStyleSheet(DARK_THEME)
    return application


def main() -> int:
    """Run the IT Radar desktop application."""
    application = create_application()
    event_loop = QEventLoop(application)
    asyncio.set_event_loop(event_loop)
    window = MainWindow(LocalDashboardProvider(), LocalOpportunityProvider())
    window.show()
    event_loop.create_task(window.dashboard_view.refresh())
    event_loop.create_task(window.opportunities_view.load(initial=True))
    application.aboutToQuit.connect(event_loop.stop)
    with event_loop:
        event_loop.run_forever()
    return 0
