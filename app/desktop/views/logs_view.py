from PySide6.QtCore import QDate, QObject, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.logging import LogBufferHandler, LogEntry, desktop_log_buffer


class LogSignalBridge(QObject):
    received = Signal(object)


class LogsView(QWidget):
    columns = ("Time", "Level", "Source", "Module", "Message")
    level_colors = {
        "DEBUG": "#8e98aa",
        "INFO": "#75b7ff",
        "WARNING": "#f0b44c",
        "ERROR": "#ef6262",
        "CRITICAL": "#ff4d6d",
    }

    def __init__(
        self,
        handler: LogBufferHandler | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.handler = handler or desktop_log_buffer
        self.entries: list[LogEntry] = []
        self.paused = False
        self.bridge = LogSignalBridge(self)
        self.bridge.received.connect(self.append_entry)
        self._listener = self.bridge.received.emit
        self.setObjectName("logsView")
        self._build_ui()
        self.handler.subscribe(self._listener)
        self.set_entries(self.handler.snapshot())

    def _build_ui(self) -> None:
        title = QLabel("Logs")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Журнал приложения в реальном времени")
        subtitle.setObjectName("pageDescription")

        self.source_filter = QLineEdit()
        self.source_filter.setPlaceholderText("Source")
        self.module_filter = QLineEdit()
        self.module_filter.setPlaceholderText("Module")
        self.level_filter = QComboBox()
        self.level_filter.addItem("All levels", None)
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            self.level_filter.addItem(level, level)
        self.date_enabled = QCheckBox("Date")
        self.date_filter = QDateEdit(QDate.currentDate())
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setEnabled(False)
        self.date_enabled.toggled.connect(self.date_filter.setEnabled)
        for widget in (
            self.source_filter,
            self.module_filter,
            self.level_filter,
            self.date_filter,
        ):
            if isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self.refresh)
            elif isinstance(widget, QDateEdit):
                widget.dateChanged.connect(self.refresh)
            else:
                widget.textChanged.connect(self.refresh)
        self.date_enabled.toggled.connect(self.refresh)

        self.pause_button = QPushButton("PAUSE")
        self.pause_button.setObjectName("secondaryButton")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.clear_button = QPushButton("CLEAR VIEW")
        self.clear_button.setObjectName("secondaryButton")
        self.clear_button.clicked.connect(self.clear_view)
        filters = QHBoxLayout()
        filters.addWidget(self.source_filter)
        filters.addWidget(self.module_filter)
        filters.addWidget(self.level_filter)
        filters.addWidget(self.date_enabled)
        filters.addWidget(self.date_filter)
        filters.addWidget(self.pause_button)
        filters.addWidget(self.clear_button)

        self.table = QTableWidget(0, len(self.columns))
        self.table.setObjectName("logsTable")
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, header.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, header.ResizeMode.ResizeToContents)

        self.feedback = QLabel("Live logging active")
        self.feedback.setObjectName("dashboardFeedback")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 28)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(filters)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.feedback)

    def set_entries(self, entries: list[LogEntry]) -> None:
        self.entries = list(entries)
        self.refresh()

    def append_entry(self, entry: LogEntry) -> None:
        self.entries.append(entry)
        if len(self.entries) > 2_000:
            del self.entries[: len(self.entries) - 2_000]
        if not self.paused and self._matches(entry):
            self._append_row(entry)
            self.table.scrollToBottom()
        self._update_feedback()

    def refresh(self, *_args: object) -> None:
        visible = [entry for entry in self.entries if self._matches(entry)]
        self.table.setRowCount(0)
        for entry in visible:
            self._append_row(entry)
        self.table.scrollToBottom()
        self._update_feedback()

    def _matches(self, entry: LogEntry) -> bool:
        source = self.source_filter.text().strip().casefold()
        module = self.module_filter.text().strip().casefold()
        level = self.level_filter.currentData()
        selected_date = self.date_filter.date().toPython()
        return (
            (not source or source in (entry.source or "").casefold())
            and (not module or module in entry.logger.casefold())
            and (level is None or entry.level == level)
            and (
                not self.date_enabled.isChecked()
                or entry.timestamp.astimezone().date() == selected_date
            )
        )

    def _append_row(self, entry: LogEntry) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = (
            entry.timestamp.astimezone().strftime("%d.%m.%Y %H:%M:%S"),
            entry.level,
            entry.source or "—",
            entry.logger,
            entry.message,
        )
        color = QColor(self.level_colors.get(entry.level, "#d5dae3"))
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            if column == 1:
                item.setForeground(color)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, column, item)

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_button.setText("RESUME" if self.paused else "PAUSE")
        if not self.paused:
            self.refresh()
        else:
            self._update_feedback()

    def clear_view(self) -> None:
        self.entries.clear()
        self.refresh()

    def _update_feedback(self) -> None:
        state = "paused" if self.paused else "live"
        self.feedback.setText(
            f"{state}: {self.table.rowCount()} shown / {len(self.entries)} buffered"
        )

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.handler.unsubscribe(self._listener)
        super().closeEvent(event)
