import asyncio
from decimal import Decimal

from PySide6.QtCore import QModelIndex, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.desktop.models import OpportunityTableModel
from app.desktop.services.opportunities import OpportunityProvider
from app.schemas.opportunity_management import OpportunityFilters, OpportunitySortField


class OpportunitiesView(QWidget):
    opportunity_activated = Signal(int)
    sort_fields: tuple[OpportunitySortField, ...] = (
        "score",
        "title",
        "source",
        "type",
        "category",
        "category",
        "budget",
        "published",
        "status",
    )

    def __init__(
        self,
        provider: OpportunityProvider | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.provider = provider
        self.current_page = 1
        self.total_pages = 1
        self.sort_by: OpportunitySortField = "published"
        self.sort_descending = True
        self._filter_values_loaded = False
        self.setObjectName("opportunitiesView")
        self._build_ui()

    def _build_ui(self) -> None:
        title = QLabel("Opportunities")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Поиск и отбор найденных возможностей")
        subtitle.setObjectName("pageDescription")
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.clicked.connect(self.request_refresh)

        heading = QHBoxLayout()
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(self.refresh_button)

        filters = self._build_filters()
        self.model = OpportunityTableModel()
        self.table = QTableView()
        self.table.setObjectName("opportunityManagementTable")
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._activate_row)
        header = self.table.horizontalHeader()
        header.setSortIndicator(7, Qt.SortOrder.DescendingOrder)
        header.sortIndicatorChanged.connect(self._sort_changed)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        self.previous_button = QPushButton("← Назад")
        self.next_button = QPushButton("Вперёд →")
        self.previous_button.clicked.connect(self._previous_page)
        self.next_button.clicked.connect(self._next_page)
        self.page_label = QLabel("Страница 1 из 1")
        self.page_label.setObjectName("paginationLabel")
        self.result_label = QLabel("0 результатов")
        self.result_label.setObjectName("dashboardFeedback")

        pagination = QHBoxLayout()
        pagination.addWidget(self.result_label)
        pagination.addStretch()
        pagination.addWidget(self.previous_button)
        pagination.addWidget(self.page_label)
        pagination.addWidget(self.next_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 28)
        layout.setSpacing(12)
        layout.addLayout(heading)
        layout.addWidget(subtitle)
        layout.addWidget(filters)
        layout.addWidget(self.table, 1)
        layout.addLayout(pagination)
        self._update_pagination()

    def _build_filters(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("filterPanel")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по заголовку и описанию…")
        self.market_combo = self._combo(
            (("Все рынки", "all"), ("Россия", "ru"), ("International", "international"))
        )
        self.type_combo = self._combo(
            (
                ("Все типы", None),
                ("Project", "project"),
                ("Freelance", "freelance"),
                ("Tender", "tender"),
                ("Contract", "contract"),
                ("Vacancy", "vacancy"),
            )
        )
        self.source_combo = self._combo((("Все источники", None),))
        self.category_combo = self._combo((("Все категории", None),))
        self.technology_edit = QLineEdit()
        self.technology_edit.setPlaceholderText("Технология")
        self.budget_from = self._money_spin("Бюджет от")
        self.budget_to = self._money_spin("Бюджет до")
        self.score_from = QSpinBox()
        self.score_from.setRange(0, 100)
        self.score_from.setSpecialValueText("Score любой")
        self.score_from.setSuffix("%")
        self.published_combo = self._combo(
            (
                ("За всё время", None),
                ("Сегодня", 0),
                ("24 часа", 1),
                ("3 дня", 3),
                ("7 дней", 7),
                ("30 дней", 30),
            )
        )
        self.status_combo = self._combo(
            (
                ("Все статусы", None),
                ("New", "new"),
                ("Interesting", "interesting"),
                ("Reviewing", "reviewing"),
                ("Responded", "responded"),
                ("Won", "won"),
                ("Lost", "lost"),
                ("Ignored", "ignored"),
            )
        )
        apply_button = QPushButton("Применить")
        apply_button.setObjectName("primaryButton")
        reset_button = QPushButton("Сбросить")
        reset_button.setObjectName("secondaryButton")
        apply_button.clicked.connect(self._apply_filters)
        reset_button.clicked.connect(self._reset_filters)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(350)
        self.search_timer.timeout.connect(self._apply_filters)
        self.search_edit.textChanged.connect(lambda: self.search_timer.start())

        layout = QGridLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)
        layout.addWidget(self.search_edit, 0, 0, 1, 3)
        layout.addWidget(self.market_combo, 0, 3)
        layout.addWidget(self.type_combo, 0, 4)
        layout.addWidget(self.published_combo, 0, 5)
        layout.addWidget(self.source_combo, 1, 0)
        layout.addWidget(self.category_combo, 1, 1)
        layout.addWidget(self.technology_edit, 1, 2)
        layout.addWidget(self.budget_from, 1, 3)
        layout.addWidget(self.budget_to, 1, 4)
        layout.addWidget(self.score_from, 1, 5)
        layout.addWidget(self.status_combo, 2, 0)
        layout.addWidget(reset_button, 2, 4)
        layout.addWidget(apply_button, 2, 5)
        return panel

    @staticmethod
    def _combo(values: tuple[tuple[str, object], ...]) -> QComboBox:
        combo = QComboBox()
        for label, value in values:
            combo.addItem(label, value)
        return combo

    @staticmethod
    def _money_spin(placeholder: str) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0, 1_000_000_000)
        spin.setDecimals(0)
        spin.setSingleStep(10_000)
        spin.setSpecialValueText(placeholder)
        return spin

    def request_initial_load(self) -> None:
        asyncio.create_task(self.load(initial=True))

    def request_refresh(self) -> None:
        asyncio.create_task(self.load())

    async def load(self, *, initial: bool = False) -> None:
        if self.provider is None:
            self.result_label.setText("Источник данных не настроен")
            return
        self.refresh_button.setEnabled(False)
        self.result_label.setText("Загрузка…")
        try:
            if initial and not self._filter_values_loaded:
                sources, categories = await self.provider.filter_values()
                self._set_filter_values(sources, categories)
                self._filter_values_loaded = True
            page = await self.provider.search(self._filters())
        except Exception:
            self.result_label.setText("Не удалось загрузить данные. Проверьте подключение к БД.")
        else:
            self.model.set_items(page.items)
            self.current_page = page.page
            self.total_pages = page.total_pages
            self.result_label.setText(f"Найдено: {page.total}")
            self._update_pagination()
        finally:
            self.refresh_button.setEnabled(True)

    def _filters(self) -> OpportunityFilters:
        return OpportunityFilters(
            search=self.search_edit.text().strip(),
            market=self.market_combo.currentData(),
            opportunity_type=self.type_combo.currentData(),
            source=self.source_combo.currentData(),
            category=self.category_combo.currentData(),
            technology=self.technology_edit.text().strip() or None,
            budget_from=self._decimal_or_none(self.budget_from.value()),
            budget_to=self._decimal_or_none(self.budget_to.value()),
            score_from=self.score_from.value() or None,
            published_days=self.published_combo.currentData(),
            status=self.status_combo.currentData(),
            sort_by=self.sort_by,
            sort_descending=self.sort_descending,
            page=self.current_page,
        )

    @staticmethod
    def _decimal_or_none(value: float) -> Decimal | None:
        return Decimal(str(int(value))) if value else None

    def _set_filter_values(
        self, sources: list[tuple[str, str]], categories: list[str]
    ) -> None:
        self.source_combo.clear()
        self.source_combo.addItem("Все источники", None)
        for code, name in sources:
            self.source_combo.addItem(name, code)
        self.category_combo.clear()
        self.category_combo.addItem("Все категории", None)
        for category in categories:
            self.category_combo.addItem(category, category)

    def _apply_filters(self) -> None:
        self.current_page = 1
        self.request_refresh()

    def _reset_filters(self) -> None:
        self.search_edit.clear()
        self.technology_edit.clear()
        self.budget_from.setValue(0)
        self.budget_to.setValue(0)
        self.score_from.setValue(0)
        for combo in (
            self.market_combo,
            self.type_combo,
            self.source_combo,
            self.category_combo,
            self.published_combo,
            self.status_combo,
        ):
            combo.setCurrentIndex(0)
        self._apply_filters()

    def _sort_changed(self, column: int, order: Qt.SortOrder) -> None:
        if 0 <= column < len(self.sort_fields):
            self.sort_by = self.sort_fields[column]
            self.sort_descending = order == Qt.SortOrder.DescendingOrder
            self.current_page = 1
            self.request_refresh()

    def _previous_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self.request_refresh()

    def _next_page(self) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.request_refresh()

    def _update_pagination(self) -> None:
        self.page_label.setText(f"Страница {self.current_page} из {self.total_pages}")
        self.previous_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)

    def _activate_row(self, index: QModelIndex) -> None:
        row = index.row()
        opportunity_id = self.model.opportunity_id(row)
        if opportunity_id is not None:
            self.opportunity_activated.emit(opportunity_id)
