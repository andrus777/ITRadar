import asyncio
from decimal import Decimal

from pydantic import ValidationError
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.desktop.services.profile import DeveloperProfileProvider
from app.schemas import DeveloperProfile


class DeveloperProfileView(QWidget):
    def __init__(
        self,
        provider: DeveloperProfileProvider | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.provider = provider
        self.profile_id: int | None = None
        self.setObjectName("developerProfileView")
        self._build_ui()

    def _build_ui(self) -> None:
        title = QLabel("Developer Profile")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Критерии персонального отбора возможностей")
        subtitle.setObjectName("pageDescription")

        panel = QFrame()
        panel.setObjectName("profilePanel")
        form = QFormLayout(panel)
        self.name_edit = QLineEdit()
        self.categories_edit = QLineEdit()
        self.categories_edit.setPlaceholderText("backend, automation, api")
        self.exclusions_edit = QLineEdit()
        self.exclusions_edit.setPlaceholderText("wordpress, gambling, unpaid")
        self.min_budget = self._budget_box()
        self.max_budget = self._budget_box()
        form.addRow("Name", self.name_edit)
        form.addRow("Categories", self.categories_edit)
        form.addRow("Minimum budget", self.min_budget)
        form.addRow("Maximum budget", self.max_budget)
        form.addRow("Exclude keywords", self.exclusions_edit)

        skills_label = QLabel("TECHNOLOGIES AND WEIGHTS")
        skills_label.setObjectName("sectionTitle")
        self.skills = QTableWidget(0, 2)
        self.skills.setObjectName("profileSkillsTable")
        self.skills.setHorizontalHeaderLabels(("Technology", "Weight 1–10"))
        self.skills.horizontalHeader().setStretchLastSection(False)
        self.skills.horizontalHeader().setSectionResizeMode(
            0, self.skills.horizontalHeader().ResizeMode.Stretch
        )
        self.skills.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.skills.verticalHeader().setVisible(False)
        add_button = QPushButton("Add technology")
        add_button.setObjectName("secondaryButton")
        add_button.clicked.connect(lambda: self.add_skill("", 5))
        remove_button = QPushButton("Remove selected")
        remove_button.setObjectName("secondaryButton")
        remove_button.clicked.connect(self.remove_selected_skill)
        skill_actions = QHBoxLayout()
        skill_actions.addWidget(add_button)
        skill_actions.addWidget(remove_button)
        skill_actions.addStretch()

        self.save_button = QPushButton("SAVE PROFILE")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self.request_save)
        self.feedback = QLabel("Загрузка профиля…")
        self.feedback.setObjectName("dashboardFeedback")
        bottom = QHBoxLayout()
        bottom.addWidget(self.feedback, 1)
        bottom.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 28)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(panel)
        layout.addWidget(skills_label)
        layout.addWidget(self.skills, 1)
        layout.addLayout(skill_actions)
        layout.addLayout(bottom)

    @staticmethod
    def _budget_box() -> QDoubleSpinBox:
        field = QDoubleSpinBox()
        field.setRange(-1, 999_999_999)
        field.setDecimals(0)
        field.setSpecialValueText("Not set")
        field.setValue(-1)
        field.setSuffix(" ₽")
        return field

    async def load(self) -> None:
        if self.provider is None:
            self.feedback.setText("Сервис профиля не настроен")
            return
        self.save_button.setEnabled(False)
        try:
            self.set_profile(await self.provider.load())
        except Exception:
            self.feedback.setText("Не удалось загрузить профиль")
        else:
            self.feedback.setText("Профиль загружен")
        finally:
            self.save_button.setEnabled(True)

    def set_profile(self, profile: DeveloperProfile) -> None:
        self.profile_id = profile.profile_id
        self.name_edit.setText(profile.name)
        self.categories_edit.setText(", ".join(profile.categories))
        self.exclusions_edit.setText(", ".join(profile.exclude_keywords))
        self.min_budget.setValue(
            float(profile.min_budget) if profile.min_budget is not None else -1
        )
        self.max_budget.setValue(
            float(profile.max_budget) if profile.max_budget is not None else -1
        )
        self.skills.setRowCount(0)
        for technology, weight in sorted(profile.technology_weights.items()):
            self.add_skill(technology, weight)

    def add_skill(self, technology: str, weight: int) -> None:
        row = self.skills.rowCount()
        self.skills.insertRow(row)
        self.skills.setItem(row, 0, QTableWidgetItem(technology))
        weight_field = QSpinBox()
        weight_field.setRange(1, 10)
        weight_field.setValue(weight)
        weight_field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.skills.setCellWidget(row, 1, weight_field)
        if not technology:
            self.skills.editItem(self.skills.item(row, 0))

    def remove_selected_skill(self) -> None:
        for row in sorted({index.row() for index in self.skills.selectedIndexes()}, reverse=True):
            self.skills.removeRow(row)

    def request_save(self) -> None:
        asyncio.create_task(self.save())

    async def save(self) -> None:
        if self.provider is None or self.profile_id is None:
            return
        try:
            profile = self.form_profile()
        except ValidationError:
            self.feedback.setText("Проверьте имя, веса и диапазон бюджета")
            return
        self.save_button.setEnabled(False)
        try:
            self.set_profile(await self.provider.save(profile))
        except Exception:
            self.feedback.setText("Не удалось сохранить профиль")
        else:
            self.feedback.setText("Профиль сохранён")
        finally:
            self.save_button.setEnabled(True)

    def form_profile(self) -> DeveloperProfile:
        weights: dict[str, int] = {}
        for row in range(self.skills.rowCount()):
            technology = self.skills.item(row, 0).text().strip()
            weight = self.skills.cellWidget(row, 1)
            if technology and isinstance(weight, QSpinBox):
                weights[technology] = weight.value()
        return DeveloperProfile(
            profile_id=self.profile_id,
            name=self.name_edit.text().strip(),
            technology_weights=weights,
            categories=self._terms(self.categories_edit.text()),
            min_budget=self._amount(self.min_budget.value()),
            max_budget=self._amount(self.max_budget.value()),
            exclude_keywords=self._terms(self.exclusions_edit.text()),
        )

    @staticmethod
    def _terms(value: str) -> list[str]:
        return [term.strip() for term in value.split(",") if term.strip()]

    @staticmethod
    def _amount(value: float) -> Decimal | None:
        return None if value < 0 else Decimal(str(int(value)))
