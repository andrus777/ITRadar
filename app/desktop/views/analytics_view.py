import asyncio

from PySide6.QtWidgets import (
    QComboBox,
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

from app.desktop.services.analytics import AnalyticsProvider
from app.schemas.analytics import AnalyticsPoint, AnalyticsSnapshot


class AnalyticsView(QWidget):
    def __init__(
        self, provider: AnalyticsProvider | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.provider = provider
        self.setObjectName("analyticsView")
        self._build_ui()

    def _build_ui(self) -> None:
        title = QLabel("Analytics")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Динамика возможностей и структура спроса")
        subtitle.setObjectName("pageDescription")
        self.period = QComboBox()
        for days in (7, 30, 90):
            self.period.addItem(f"{days} days", days)
        self.period.setCurrentIndex(1)
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.clicked.connect(self.request_refresh)
        heading = QHBoxLayout()
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(self.period)
        heading.addWidget(self.refresh_button)

        self.daily_table = self._table("Date", "Opportunities")
        self.source_table = self._table("Source", "Count")
        self.category_table = self._table("Category", "Count")
        self.technology_table = self._table("Technology", "Count")
        grid = QGridLayout()
        for index, (label, table) in enumerate(
            (
                ("OPPORTUNITIES / DAY", self.daily_table),
                ("SOURCES", self.source_table),
                ("CATEGORIES", self.category_table),
                ("TECHNOLOGIES", self.technology_table),
            )
        ):
            panel = QVBoxLayout()
            heading_label = QLabel(label)
            heading_label.setObjectName("sectionTitle")
            panel.addWidget(heading_label)
            panel.addWidget(table)
            grid.addLayout(panel, index // 2, index % 2)

        self.feedback = QLabel("Нажмите «Обновить» для загрузки аналитики")
        self.feedback.setObjectName("dashboardFeedback")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 28)
        layout.setSpacing(12)
        layout.addLayout(heading)
        layout.addWidget(subtitle)
        layout.addLayout(grid, 1)
        layout.addWidget(self.feedback)

    @staticmethod
    def _table(first: str, second: str) -> QTableWidget:
        table = QTableWidget(0, 2)
        table.setObjectName("analyticsTable")
        table.setHorizontalHeaderLabels((first, second))
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().hide()
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        return table

    def request_refresh(self) -> None:
        asyncio.create_task(self.refresh())

    async def refresh(self) -> None:
        if self.provider is None:
            self.feedback.setText("Сервис аналитики не настроен")
            return
        self.refresh_button.setEnabled(False)
        try:
            snapshot = await self.provider.load(int(self.period.currentData()))
        except Exception:
            self.feedback.setText("Не удалось загрузить аналитику")
        else:
            self.render(snapshot)
            self.feedback.setText(f"Период: {snapshot.days} дней")
        finally:
            self.refresh_button.setEnabled(True)

    def render(self, snapshot: AnalyticsSnapshot) -> None:
        self._fill(
            self.daily_table,
            [
                AnalyticsPoint(label=row.day.strftime("%d.%m.%Y"), count=row.count)
                for row in snapshot.opportunities_by_day
            ],
        )
        self._fill(self.source_table, snapshot.sources)
        self._fill(self.category_table, snapshot.categories)
        self._fill(self.technology_table, snapshot.technologies)

    @staticmethod
    def _fill(table: QTableWidget, values: list[AnalyticsPoint]) -> None:
        table.setRowCount(len(values))
        for row, value in enumerate(values):
            table.setItem(row, 0, QTableWidgetItem(value.label))
            table.setItem(row, 1, QTableWidgetItem(str(value.count)))
