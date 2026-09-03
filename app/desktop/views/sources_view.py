import asyncio
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.desktop.services.sources import SourceProvider
from app.schemas.source_management import SourceSummary


class SourcesView(QWidget):
    columns = (
        "Enabled",
        "Source",
        "Market",
        "Type",
        "Priority",
        "Status",
        "Last Run",
        "New Items",
        "Errors",
    )

    def __init__(
        self,
        provider: SourceProvider | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.provider = provider
        self.sources: list[SourceSummary] = []
        self.setObjectName("sourcesView")
        self._build_ui()

    def _build_ui(self) -> None:
        title = QLabel("Sources")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Состояние и управление источниками данных")
        subtitle.setObjectName("pageDescription")
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.clicked.connect(self.request_load)

        heading = QHBoxLayout()
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(self.refresh_button)

        self.table = QTableWidget(0, len(self.columns))
        self.table.setObjectName("sourcesTable")
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.details_panel = QFrame()
        self.details_panel.setObjectName("sourceDetailsPanel")
        self.details_layout = QGridLayout(self.details_panel)
        self.details_layout.setContentsMargins(16, 12, 16, 12)
        self.details_layout.setHorizontalSpacing(20)
        self.details_layout.setVerticalSpacing(6)

        self.toggle_button = QPushButton("Enable / Disable")
        self.toggle_button.setObjectName("secondaryButton")
        self.toggle_button.clicked.connect(self.request_toggle)
        self.run_button = QPushButton("Run Source")
        self.run_button.setObjectName("primaryButton")
        self.run_button.clicked.connect(self.request_run)
        self.feedback = QLabel("Загрузка источников…")
        self.feedback.setObjectName("dashboardFeedback")

        actions = QHBoxLayout()
        actions.addWidget(self.feedback, 1)
        actions.addWidget(self.toggle_button)
        actions.addWidget(self.run_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 28)
        layout.setSpacing(12)
        layout.addLayout(heading)
        layout.addWidget(subtitle)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.details_panel)
        layout.addLayout(actions)
        self._set_actions_enabled(False)

    def request_load(self) -> None:
        asyncio.create_task(self.load())

    async def load(self) -> None:
        if self.provider is None:
            self.feedback.setText("Сервис источников не настроен")
            return
        self.refresh_button.setEnabled(False)
        self.feedback.setText("Загрузка…")
        selected_code = self.selected_source().code if self.selected_source() else None
        try:
            sources = await self.provider.list_sources()
        except Exception:
            self.feedback.setText("Не удалось загрузить источники. Проверьте подключение к БД.")
        else:
            self.set_sources(sources, selected_code=selected_code)
            self.feedback.setText(f"Источников: {len(sources)}")
        finally:
            self.refresh_button.setEnabled(True)

    def set_sources(
        self, sources: list[SourceSummary], *, selected_code: str | None = None
    ) -> None:
        self.sources = sources
        self.table.setRowCount(len(sources))
        selected_row = 0
        for row, source in enumerate(sources):
            values = (
                "✓" if source.enabled else "—",
                source.name,
                source.market,
                source.collection_method,
                source.priority,
                source.health if source.enabled else "disabled",
                self._format_date(source.last_run_at),
                str(source.items_new),
                str(source.items_rejected),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, source.code)
                if column in {0, 4, 5, 7, 8}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, item)
            if source.code == selected_code:
                selected_row = row
        if sources:
            self.table.selectRow(selected_row)
        else:
            self._set_actions_enabled(False)
            self._show_details(None)

    def selected_source(self) -> SourceSummary | None:
        row = self.table.currentRow()
        return self.sources[row] if 0 <= row < len(self.sources) else None

    def _selection_changed(self) -> None:
        source = self.selected_source()
        self._show_details(source)
        self._set_actions_enabled(source is not None)

    def _show_details(self, source: SourceSummary | None) -> None:
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        if source is None:
            self.details_layout.addWidget(QLabel("Источник не выбран"), 0, 0)
            return
        values = (
            ("Code", source.code),
            ("URL", source.base_url),
            ("Method", source.collection_method),
            ("Poll interval", f"{source.poll_interval_minutes} min"),
            ("Received", str(source.items_received)),
            ("New", str(source.items_new)),
            ("Duplicates", str(source.items_duplicate)),
            ("Rejected", str(source.items_rejected)),
            ("Last status", source.last_run_status or "never run"),
            ("Last error", source.last_error or "—"),
        )
        for index, (label, value) in enumerate(values):
            key = QLabel(f"{label}:")
            key.setObjectName("metadataKey")
            value_label = QLabel(value)
            value_label.setWordWrap(True)
            self.details_layout.addWidget(key, index // 2, (index % 2) * 2)
            self.details_layout.addWidget(value_label, index // 2, (index % 2) * 2 + 1)

    def request_toggle(self) -> None:
        asyncio.create_task(self.toggle_selected())

    async def toggle_selected(self) -> None:
        source = self.selected_source()
        if source is None or self.provider is None:
            return
        self._set_busy(True)
        try:
            await self.provider.set_enabled(source.code, not source.enabled)
            await self.load()
        except Exception:
            self.feedback.setText("Не удалось изменить состояние источника")
        finally:
            self._set_busy(False)

    def request_run(self) -> None:
        asyncio.create_task(self.run_selected())

    async def run_selected(self) -> None:
        source = self.selected_source()
        if source is None or self.provider is None:
            return
        self._set_busy(True)
        self.feedback.setText(f"Сбор {source.name}…")
        try:
            result = await self.provider.run_source(source.code)
            await self.load()
        except ValueError:
            self.feedback.setText("Источник отключён")
        except Exception:
            self.feedback.setText("Сбор завершился ошибкой")
        else:
            self.feedback.setText(
                f"{result.status}: получено {result.items_received}, новых {result.items_new}"
            )
        finally:
            self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        self.refresh_button.setEnabled(not busy)
        self.table.setEnabled(not busy)
        self._set_actions_enabled(not busy and self.selected_source() is not None)

    def _set_actions_enabled(self, enabled: bool) -> None:
        source = self.selected_source()
        self.toggle_button.setEnabled(enabled and source is not None)
        self.run_button.setEnabled(
            enabled
            and source is not None
            and source.enabled
            and source.adapter_available
        )
        if source is not None:
            self.toggle_button.setText("Disable" if source.enabled else "Enable")

    @staticmethod
    def _format_date(value: datetime | None) -> str:
        return value.astimezone().strftime("%d.%m.%Y %H:%M") if value else "—"
