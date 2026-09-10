import asyncio
from datetime import datetime
from decimal import Decimal

from PySide6.QtCore import QThreadPool, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.desktop.services.background_worker import BackgroundWorker
from app.desktop.services.telegram import TelegramAction, TelegramProvider
from app.schemas import TelegramActionResult, TelegramConfiguration, TelegramOverview


class TelegramView(QWidget):
    action_completed = Signal(str)

    def __init__(
        self, provider: TelegramProvider | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.provider = provider
        self.worker: BackgroundWorker | None = None
        self.bot_configured = False
        self.setObjectName("telegramView")
        self._build_ui()

    def _build_ui(self) -> None:
        title = QLabel("Telegram")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Статус бота, настройки и ручная отправка дайджеста")
        subtitle.setObjectName("pageDescription")
        status_panel = QFrame()
        status_panel.setObjectName("telegramPanel")
        status_form = QFormLayout(status_panel)
        self.bot_status = QLabel("Not checked")
        self.token_mask = QLabel("not configured")
        self.last_digest = QLabel("—")
        self.next_digest = QLabel("—")
        status_form.addRow("Bot", self.bot_status)
        status_form.addRow("Token", self.token_mask)
        status_form.addRow("Last digest", self.last_digest)
        status_form.addRow("Next digest", self.next_digest)

        settings_panel = QFrame()
        settings_panel.setObjectName("telegramPanel")
        form = QFormLayout(settings_panel)
        self.enabled = QCheckBox("Enabled")
        self.chat_id = QLineEdit()
        self.chat_id.setPlaceholderText("123456789")
        self.min_score = QSpinBox()
        self.min_score.setRange(0, 100)
        self.min_score.setSuffix(" %")
        self.min_budget = QLineEdit()
        self.min_budget.setPlaceholderText("Not set")
        self.max_items = QSpinBox()
        self.max_items.setRange(1, 100)
        self.include_international = QCheckBox("Include international")
        self.include_types = QLineEdit()
        self.include_types.setPlaceholderText("project, tender, job")
        form.addRow("", self.enabled)
        form.addRow("Chat ID", self.chat_id)
        form.addRow("Minimum score", self.min_score)
        form.addRow("Minimum budget", self.min_budget)
        form.addRow("Maximum items", self.max_items)
        form.addRow("", self.include_international)
        form.addRow("Include types", self.include_types)

        self.save_button = QPushButton("SAVE SETTINGS")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self.request_save)
        self.status_button = self._action_button("CHECK CONNECTION", "status")
        self.test_button = self._action_button("SEND TEST MESSAGE", "test")
        self.preview_button = self._action_button("PREVIEW DIGEST", "preview")
        self.send_button = self._action_button("SEND DIGEST NOW", "send")
        actions = QHBoxLayout()
        for button in (
            self.status_button,
            self.test_button,
            self.preview_button,
            self.send_button,
        ):
            actions.addWidget(button)
        actions.addStretch()

        self.preview = QTextBrowser()
        self.preview.setObjectName("telegramPreview")
        self.preview.setPlaceholderText("Здесь появится предварительный просмотр дайджеста")
        self.feedback = QLabel("Загрузка настроек…")
        self.feedback.setObjectName("dashboardFeedback")
        bottom = QHBoxLayout()
        bottom.addWidget(self.feedback, 1)
        bottom.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 28)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(status_panel)
        layout.addWidget(settings_panel)
        layout.addLayout(actions)
        layout.addWidget(self.preview, 1)
        layout.addLayout(bottom)

    def _action_button(self, label: str, action: TelegramAction) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("secondaryButton")
        button.clicked.connect(lambda: self.run_action(action))
        return button

    async def load(self) -> None:
        if self.provider is None:
            self.feedback.setText("Сервис Telegram не настроен")
            return
        try:
            self.set_overview(await self.provider.overview())
        except Exception:
            self.feedback.setText("Не удалось загрузить настройки Telegram")
        else:
            self.feedback.setText("Настройки Telegram загружены")

    def set_overview(self, value: TelegramOverview) -> None:
        self.token_mask.setText(value.token_mask)
        self.bot_configured = value.configured
        self.bot_status.setText("Configured" if value.configured else "Not configured")
        self.last_digest.setText(self._date(value.last_digest_at))
        self.next_digest.setText(self._date(value.next_digest_at))
        configuration = value.configuration
        self.enabled.setChecked(configuration.enabled)
        self.chat_id.setText(str(configuration.chat_id) if configuration.chat_id else "")
        self.min_score.setValue(configuration.min_score)
        self.min_budget.setText(
            str(configuration.min_budget) if configuration.min_budget is not None else ""
        )
        self.max_items.setValue(configuration.max_items)
        self.include_international.setChecked(configuration.include_international)
        self.include_types.setText(", ".join(configuration.include_types))
        self._set_busy(False)

    def configuration(self) -> TelegramConfiguration:
        chat_id = self.chat_id.text().strip()
        budget = self.min_budget.text().strip()
        return TelegramConfiguration(
            enabled=self.enabled.isChecked(),
            chat_id=int(chat_id) if chat_id else None,
            min_score=self.min_score.value(),
            min_budget=Decimal(budget) if budget else None,
            max_items=self.max_items.value(),
            include_international=self.include_international.isChecked(),
            include_types=[
                item.strip().casefold()
                for item in self.include_types.text().split(",")
                if item.strip()
            ],
        )

    def request_save(self) -> None:
        asyncio.create_task(self.save())

    async def save(self) -> None:
        if self.provider is None:
            return
        try:
            configuration = self.configuration()
        except (ValueError, ArithmeticError):
            self.feedback.setText("Проверьте Chat ID и Minimum budget")
            return
        self.save_button.setEnabled(False)
        try:
            self.set_overview(await self.provider.save(configuration))
        except Exception:
            self.feedback.setText("Не удалось сохранить настройки")
        else:
            self.feedback.setText("Настройки сохранены")
        finally:
            self.save_button.setEnabled(True)

    def run_action(self, action: TelegramAction) -> None:
        if self.provider is None or self.worker is not None:
            return
        try:
            configuration = self.configuration()
        except (ValueError, ArithmeticError):
            self.feedback.setText("Проверьте настройки Telegram")
            return
        self._set_busy(True)
        self.feedback.setText(f"Telegram: {action}…")
        self.worker = BackgroundWorker(
            lambda emit, cancel: self.provider.run_action(action, configuration, emit, cancel)
        )
        self.worker.signals.result.connect(self._action_complete)
        self.worker.signals.error.connect(self.feedback.setText)
        self.worker.signals.finished.connect(self._action_finished)
        QThreadPool.globalInstance().start(self.worker)

    def _action_complete(self, result: TelegramActionResult) -> None:
        self.feedback.setText(result.message)
        self.action_completed.emit(result.message)
        if result.message.startswith("Connected:"):
            self.bot_status.setText(result.message)
        if result.preview:
            self.preview.setHtml("<hr>".join(result.preview))

    def _action_finished(self) -> None:
        self.worker = None
        self._set_busy(False)
        if self.provider is not None:
            asyncio.create_task(self._refresh_status_dates())

    async def _refresh_status_dates(self) -> None:
        try:
            overview = await self.provider.overview()
        except Exception:
            return
        self.last_digest.setText(self._date(overview.last_digest_at))
        self.next_digest.setText(self._date(overview.next_digest_at))

    def _set_busy(self, busy: bool) -> None:
        self.save_button.setEnabled(not busy)
        self.preview_button.setEnabled(not busy)
        self.status_button.setEnabled(not busy and self.bot_configured)
        can_send = not busy and self.bot_configured and bool(self.chat_id.text().strip())
        self.test_button.setEnabled(can_send)
        self.send_button.setEnabled(can_send and self.enabled.isChecked())

    @staticmethod
    def _date(value: datetime | None) -> str:
        return value.astimezone().strftime("%d.%m.%Y %H:%M") if value else "—"
