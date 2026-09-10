import logging
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QDate

from app.desktop.app import create_application
from app.desktop.views import LogsView
from app.logging import LogBufferHandler


def emit(handler: LogBufferHandler, message: str, level: int, source: str | None = None) -> None:
    record = logging.LogRecord("app.services.collector", level, __file__, 1, message, (), None)
    if source is not None:
        record.source = source
    handler.emit(record)


def test_logs_view_updates_live_and_filters_source_module_and_severity() -> None:
    create_application(["it-radar-logs-test"])
    handler = LogBufferHandler()
    view = LogsView(handler)

    emit(handler, "collection started", logging.INFO, "fl_ru")
    emit(handler, "source timeout", logging.WARNING, "workspace")
    assert view.table.rowCount() == 2

    view.source_filter.setText("workspace")
    assert view.table.rowCount() == 1
    assert view.table.item(0, 4).text() == "source timeout"

    view.source_filter.clear()
    view.level_filter.setCurrentIndex(view.level_filter.findData("INFO"))
    assert view.table.rowCount() == 1
    view.module_filter.setText("collector")
    assert view.table.rowCount() == 1

    view.date_enabled.setChecked(True)
    view.date_filter.setDate(QDate.currentDate().addDays(-1))
    assert view.table.rowCount() == 0
    view.date_filter.setDate(QDate.currentDate())
    assert view.table.rowCount() == 1


def test_logs_view_pause_buffers_messages_until_resume() -> None:
    create_application(["it-radar-logs-pause-test"])
    handler = LogBufferHandler()
    view = LogsView(handler)
    view.toggle_pause()
    emit(handler, "delayed", logging.ERROR)

    assert view.table.rowCount() == 0
    assert len(view.entries) == 1

    view.toggle_pause()
    assert view.table.rowCount() == 1
