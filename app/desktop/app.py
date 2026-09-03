import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from app.desktop.main_window import MainWindow
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
    window = MainWindow()
    window.show()
    return application.exec()
