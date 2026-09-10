import asyncio

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.desktop.services.settings import DesktopSettings, SettingsProvider


class SettingsView(QWidget):
    def __init__(
        self, provider: SettingsProvider | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.provider = provider or SettingsProvider()
        self.setObjectName("settingsView")
        self._build_ui()
        self.set_value(self.provider.load())

    def _build_ui(self) -> None:
        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Подключение к PostgreSQL и параметры AI-провайдера")
        subtitle.setObjectName("pageDescription")

        database = QFrame()
        database.setObjectName("settingsPanel")
        database_form = QFormLayout(database)
        self.database_url = QLineEdit()
        self.database_url.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.database_url.setPlaceholderText(
            "postgresql+asyncpg://user:password@host:5432/database"
        )
        self.database_parts = QLabel()
        self.database_url.textChanged.connect(self._update_database_parts)
        self.test_button = QPushButton("TEST CONNECTION")
        self.test_button.setObjectName("secondaryButton")
        self.test_button.clicked.connect(lambda: asyncio.create_task(self.test_connection()))
        database_form.addRow("Database URL", self.database_url)
        database_form.addRow("Host / Port / DB / User", self.database_parts)
        database_form.addRow("", self.test_button)

        ai = QFrame()
        ai.setObjectName("settingsPanel")
        ai_form = QFormLayout(ai)
        self.ai_base_url = QLineEdit()
        self.ai_model = QLineEdit()
        self.ai_api_key = QLineEdit()
        self.ai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.ai_timeout = QDoubleSpinBox()
        self.ai_timeout.setRange(1, 600)
        self.ai_timeout.setSuffix(" s")
        self.retries = QSpinBox()
        self.retries.setRange(1, 10)
        self.language = QComboBox()
        self.language.addItem("Русский", "ru")
        self.language.addItem("English", "en")
        self.ai_temperature = QDoubleSpinBox()
        self.ai_temperature.setRange(0, 2)
        self.ai_temperature.setSingleStep(0.1)
        ai_form.addRow("Provider URL", self.ai_base_url)
        ai_form.addRow("Model", self.ai_model)
        ai_form.addRow("API key", self.ai_api_key)
        ai_form.addRow("Temperature", self.ai_temperature)
        ai_form.addRow("Timeout", self.ai_timeout)
        ai_form.addRow("Retries", self.retries)
        ai_form.addRow("Язык интерфейса / Language", self.language)

        self.feedback = QLabel()
        self.feedback.setObjectName("dashboardFeedback")
        self.save_button = QPushButton("SAVE SETTINGS")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self.save)
        footer = QHBoxLayout()
        footer.addWidget(self.feedback, 1)
        footer.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 28)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(database)
        layout.addWidget(ai)
        layout.addStretch()
        layout.addLayout(footer)

    def set_value(self, value: DesktopSettings) -> None:
        self.database_url.setText(value.database_url)
        self.ai_base_url.setText(value.ai_base_url)
        self.ai_model.setText(value.ai_model)
        self.ai_api_key.setText(value.ai_api_key)
        self.ai_temperature.setValue(value.ai_temperature)
        self.ai_timeout.setValue(value.ai_timeout_seconds)
        self.retries.setValue(value.retry_attempts)
        self.language.setCurrentIndex(max(0, self.language.findData(value.language)))

    def value(self) -> DesktopSettings:
        return DesktopSettings(
            database_url=self.database_url.text().strip(),
            ai_base_url=self.ai_base_url.text().strip(),
            ai_model=self.ai_model.text().strip(),
            ai_api_key=self.ai_api_key.text(),
            ai_temperature=self.ai_temperature.value(),
            ai_timeout_seconds=self.ai_timeout.value(),
            retry_attempts=self.retries.value(),
            language=str(self.language.currentData()),
        )

    def _update_database_parts(self, value: str) -> None:
        try:
            url = self.provider.database_parts(value)
        except ValueError:
            self.database_parts.setText("Некорректный URL")
            return
        self.database_parts.setText(
            f"{url.host or '—'} / {url.port or '—'} / {url.database or '—'} / {url.username or '—'}"
        )

    def save(self) -> None:
        try:
            self.provider.save(self.value())
        except (OSError, ValueError):
            self.feedback.setText("Не удалось сохранить: проверьте параметры")
        else:
            self.feedback.setText("Сохранено в .env; перезапустите процессы IT Radar")

    async def test_connection(self) -> None:
        self.test_button.setEnabled(False)
        self.feedback.setText("Проверка подключения…")
        try:
            await self.provider.test_database(self.database_url.text().strip())
        except Exception:
            self.feedback.setText("Database unavailable")
        else:
            self.feedback.setText("Database connection OK")
        finally:
            self.test_button.setEnabled(True)
