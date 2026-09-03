import asyncio
from datetime import datetime

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.desktop.services.opportunities import OpportunityProvider
from app.schemas.opportunity_details import OpportunityDetails, OpportunityUserStatus

STATUS_OPTIONS: tuple[tuple[str, OpportunityUserStatus], ...] = (
    ("New", "new"),
    ("Interesting", "interesting"),
    ("Reviewing", "reviewing"),
    ("Responded", "responded"),
    ("Won", "won"),
    ("Lost", "lost"),
    ("Ignored", "ignored"),
)


class DetailsSection(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("detailsSection")
        section_title = QLabel(title)
        section_title.setObjectName("sectionTitle")
        self.value_label = QLabel()
        self.value_label.setObjectName("detailsSectionText")
        self.value_label.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.addWidget(section_title)
        layout.addWidget(self.value_label)


class OpportunityDialog(QDialog):
    status_changed = Signal(int, str)

    def __init__(
        self,
        opportunity_id: int,
        provider: OpportunityProvider | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.opportunity_id = opportunity_id
        self.provider = provider
        self.details: OpportunityDetails | None = None
        self.setObjectName("opportunityDialog")
        self.setWindowTitle("Opportunity Details")
        self.setMinimumSize(780, 650)
        self.resize(900, 760)
        self._build_ui()

    def _build_ui(self) -> None:
        self.title_label = QLabel("Загрузка…")
        self.title_label.setObjectName("dialogTitle")
        self.title_label.setWordWrap(True)
        self.score_label = QLabel("—")
        self.score_label.setObjectName("dialogScore")

        heading = QHBoxLayout()
        heading.addWidget(self.title_label, 1)
        heading.addWidget(self.score_label)

        self.metadata = QGridLayout()
        self.metadata.setHorizontalSpacing(20)
        self.metadata.setVerticalSpacing(7)

        self.description = QTextBrowser()
        self.description.setObjectName("detailsText")
        self.description.setOpenExternalLinks(False)

        self.ai_summary = self._section("AI ANALYSIS")
        self.matching = self._section("ПОЧЕМУ ПОДХОДИТ")
        self.risks = self._section("РИСКИ")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(14)
        content_layout.addLayout(heading)
        content_layout.addLayout(self.metadata)
        content_layout.addWidget(self._section_title("DESCRIPTION"))
        content_layout.addWidget(self.description)
        content_layout.addWidget(self.ai_summary)
        content_layout.addWidget(self.matching)
        content_layout.addWidget(self.risks)

        scroll = QScrollArea()
        scroll.setObjectName("detailsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)

        self.status_combo = QComboBox()
        for label, status in STATUS_OPTIONS:
            self.status_combo.addItem(label, status)
        self.save_status_button = QPushButton("Сохранить статус")
        self.save_status_button.setObjectName("secondaryButton")
        self.save_status_button.clicked.connect(self.request_status_save)
        self.open_button = QPushButton("Открыть источник")
        self.open_button.setObjectName("primaryButton")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_source)
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        self.feedback = QLabel("")
        self.feedback.setObjectName("dashboardFeedback")

        actions = QHBoxLayout()
        actions.addWidget(QLabel("Статус:"))
        actions.addWidget(self.status_combo)
        actions.addWidget(self.save_status_button)
        actions.addWidget(self.feedback, 1)
        actions.addWidget(self.open_button)
        actions.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.addWidget(scroll, 1)
        layout.addLayout(actions)

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    @staticmethod
    def _section(title: str) -> DetailsSection:
        return DetailsSection(title)

    def request_load(self) -> None:
        asyncio.create_task(self.load())

    async def load(self) -> None:
        if self.provider is None:
            self.feedback.setText("Сервис карточки не настроен")
            return
        try:
            details = await self.provider.details(self.opportunity_id)
        except Exception:
            self.feedback.setText("Не удалось загрузить карточку")
            return
        if details is None:
            self.feedback.setText("Opportunity не найдена")
            return
        self.set_details(details)

    def set_details(self, details: OpportunityDetails) -> None:
        self.details = details
        self.title_label.setText(details.title)
        self.score_label.setText(f"{details.score}%" if details.score is not None else "—")
        self.score_label.setProperty("level", self._score_level(details.score))
        self.style().unpolish(self.score_label)
        self.style().polish(self.score_label)
        self._set_metadata(details)
        self.description.setPlainText(details.description or "Описание отсутствует")
        ai_lines = [details.ai_summary or "AI-анализ отсутствует"]
        if details.commercial_score is not None:
            ai_lines.append(f"Commercial score: {details.commercial_score}/100")
        if details.complexity is not None:
            ai_lines.append(f"Complexity: {details.complexity}/5")
        if details.budget_comment:
            ai_lines.append(f"Budget: {details.budget_comment}")
        self.ai_summary.value_label.setText("\n".join(ai_lines))
        self.matching.value_label.setText(
            "\n".join(f"✓ {reason}" for reason in details.matching_reasons)
            or "Объяснение matching отсутствует"
        )
        self.risks.value_label.setText(
            "\n".join(f"! {risk}" for risk in details.risk_flags) or "Риски не выявлены"
        )
        index = self.status_combo.findData(details.user_status)
        self.status_combo.setCurrentIndex(max(index, 0))
        self.open_button.setEnabled(self._source_url() is not None)
        self.feedback.setText("")

    def _set_metadata(self, details: OpportunityDetails) -> None:
        while self.metadata.count():
            item = self.metadata.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        values = (
            ("Source", details.source),
            ("Published", self._format_date(details.published_at)),
            ("Budget", details.budget or "—"),
            ("Deadline", self._format_date(details.deadline_at)),
            ("Type", details.opportunity_type),
            ("Market", details.market),
            ("Category", details.ai_category or details.category),
            ("Technologies", ", ".join(details.ai_technologies or details.technologies) or "—"),
            ("Customer", details.customer or "—"),
        )
        for row, (label, value) in enumerate(values):
            key = QLabel(f"{label}:")
            key.setObjectName("metadataKey")
            self.metadata.addWidget(key, row // 2, (row % 2) * 2)
            self.metadata.addWidget(QLabel(value), row // 2, (row % 2) * 2 + 1)

    def request_status_save(self) -> None:
        asyncio.create_task(self.save_status())

    async def save_status(self) -> None:
        if self.provider is None:
            return
        status = self.status_combo.currentData()
        self.save_status_button.setEnabled(False)
        try:
            await self.provider.set_user_status(self.opportunity_id, status)
        except ValueError:
            self.feedback.setText("Сначала настройте Developer Profile")
        except Exception:
            self.feedback.setText("Не удалось сохранить статус")
        else:
            self.feedback.setText("Статус сохранён")
            self.status_changed.emit(self.opportunity_id, status)
            if self.details is not None:
                self.details = self.details.model_copy(update={"user_status": status})
        finally:
            self.save_status_button.setEnabled(True)

    def open_source(self) -> None:
        url = self._source_url()
        if url is not None:
            QDesktopServices.openUrl(url)

    def _source_url(self) -> QUrl | None:
        if self.details is None:
            return None
        url = QUrl.fromUserInput(self.details.source_url)
        return url if url.isValid() and url.scheme() in {"http", "https"} else None

    @staticmethod
    def _score_level(score: int | None) -> str:
        if score is None:
            return "none"
        if score >= 90:
            return "excellent"
        if score >= 80:
            return "good"
        if score >= 70:
            return "medium"
        return "low"

    @staticmethod
    def _format_date(value: datetime | None) -> str:
        return value.astimezone().strftime("%d.%m.%Y %H:%M") if value else "—"
