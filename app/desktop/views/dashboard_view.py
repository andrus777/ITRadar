import asyncio
from datetime import datetime

from PySide6.QtCore import Qt, Signal
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

from app.desktop.services import DashboardProvider
from app.schemas.dashboard import DashboardMetric, DashboardSnapshot, DashboardSystemStatus


class KpiCard(QFrame):
    def __init__(self, metric: DashboardMetric, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setProperty("metricKey", metric.key)

        label = QLabel(metric.label)
        label.setObjectName("kpiLabel")
        value = QLabel(metric.value)
        value.setObjectName("kpiValue")
        detail = QLabel(metric.detail or " ")
        detail.setObjectName("kpiDetail")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(2)
        layout.addWidget(label)
        layout.addWidget(value)
        layout.addWidget(detail)


class StatusBadge(QFrame):
    def __init__(self, status: DashboardSystemStatus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("systemStatus")
        self.setProperty("state", status.state)

        indicator = QLabel("●")
        indicator.setObjectName("statusIndicator")
        label = QLabel(status.label)
        label.setObjectName("statusLabel")
        detail = QLabel(status.detail)
        detail.setObjectName("statusDetail")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(7)
        layout.addWidget(indicator)
        layout.addWidget(label)
        layout.addWidget(detail)


class DashboardView(QWidget):
    opportunity_activated = Signal(int)

    def __init__(
        self,
        provider: DashboardProvider | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.provider = provider
        self.setObjectName("dashboardView")
        self._build_ui()

    def _build_ui(self) -> None:
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Состояние системы и лучшие возможности")
        subtitle.setObjectName("pageDescription")
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.clicked.connect(self.request_refresh)

        heading = QHBoxLayout()
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(self.refresh_button)

        self.status_layout = QHBoxLayout()
        self.status_layout.setSpacing(8)
        self.kpi_layout = QGridLayout()
        self.kpi_layout.setHorizontalSpacing(12)
        self.kpi_layout.setVerticalSpacing(12)
        for column in range(3):
            self.kpi_layout.setColumnStretch(column, 1)

        table_title = QLabel("TOP OPPORTUNITIES")
        table_title.setObjectName("sectionTitle")
        self.opportunities_table = QTableWidget(0, 6)
        self.opportunities_table.setObjectName("opportunitiesTable")
        self.opportunities_table.setHorizontalHeaderLabels(
            ["Score", "Title", "Source", "Budget", "Type", "Published"]
        )
        self.opportunities_table.setAlternatingRowColors(True)
        self.opportunities_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.opportunities_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.opportunities_table.verticalHeader().setVisible(False)
        header = self.opportunities_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in range(2, 6):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.opportunities_table.cellDoubleClicked.connect(self._activate_opportunity)

        self.feedback = QLabel("Нажмите «Обновить», чтобы загрузить данные")
        self.feedback.setObjectName("dashboardFeedback")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 28)
        layout.setSpacing(14)
        layout.addLayout(heading)
        layout.addWidget(subtitle)
        layout.addLayout(self.status_layout)
        layout.addSpacing(4)
        layout.addLayout(self.kpi_layout)
        layout.addSpacing(8)
        layout.addWidget(table_title)
        layout.addWidget(self.opportunities_table, 1)
        layout.addWidget(self.feedback)

    def request_refresh(self) -> None:
        asyncio.create_task(self.refresh())

    async def refresh(self) -> None:
        if self.provider is None:
            self.feedback.setText("Источник данных Dashboard не настроен")
            return
        self.refresh_button.setEnabled(False)
        self.feedback.setText("Загрузка данных…")
        try:
            snapshot = await self.provider.load()
        except Exception:
            self._show_database_error()
        else:
            self.set_snapshot(snapshot)
        finally:
            self.refresh_button.setEnabled(True)

    def _show_database_error(self) -> None:
        self._clear_layout(self.status_layout)
        self.status_layout.addWidget(
            StatusBadge(
                DashboardSystemStatus(
                    key="database",
                    label="Database",
                    state="failure",
                    detail="unavailable",
                )
            )
        )
        self.status_layout.addStretch()
        self.feedback.setText("База данных недоступна. Проверьте подключение и повторите попытку.")

    def set_snapshot(self, snapshot: DashboardSnapshot) -> None:
        self._clear_layout(self.status_layout)
        for status in snapshot.statuses:
            self.status_layout.addWidget(StatusBadge(status))
        self.status_layout.addStretch()

        self._clear_layout(self.kpi_layout)
        for index, metric in enumerate(snapshot.metrics):
            self.kpi_layout.addWidget(KpiCard(metric), index // 3, index % 3)

        self.opportunities_table.setRowCount(len(snapshot.opportunities))
        for row, opportunity in enumerate(snapshot.opportunities):
            values = (
                f"{opportunity.score}%",
                opportunity.title,
                opportunity.source,
                opportunity.budget or "—",
                opportunity.opportunity_type,
                self._format_date(opportunity.published_at),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, opportunity.opportunity_id)
                self.opportunities_table.setItem(row, column, item)
        self.feedback.setText(f"Обновлено: {snapshot.loaded_at.astimezone():%H:%M:%S}")

    def _activate_opportunity(self, row: int, _column: int) -> None:
        item = self.opportunities_table.item(row, 0)
        if item is not None:
            self.opportunity_activated.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    @staticmethod
    def _format_date(value: datetime | None) -> str:
        return value.astimezone().strftime("%d.%m %H:%M") if value is not None else "—"

    @staticmethod
    def _clear_layout(layout: QHBoxLayout | QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
