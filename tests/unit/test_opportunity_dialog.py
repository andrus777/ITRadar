import os
from datetime import UTC, datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from app.desktop.app import create_application
from app.desktop.dialogs import OpportunityDialog
from app.schemas.opportunity_details import OpportunityDetails, OpportunityUserStatus


class FakeDetailsProvider:
    def __init__(self) -> None:
        self.saved_status: OpportunityUserStatus | None = None

    async def details(self, opportunity_id: int) -> OpportunityDetails | None:
        assert opportunity_id == 42
        return OpportunityDetails(
            opportunity_id=42,
            title="Telegram bot + CRM",
            description="Интеграция Telegram с CRM",
            source="FL.ru",
            source_url="https://example.test/projects/42",
            published_at=datetime(2026, 9, 3, 10, 0, tzinfo=UTC),
            deadline_at=None,
            budget="180–250 тыс. ₽",
            category="backend",
            technologies=["python"],
            customer="Example customer",
            opportunity_type="project",
            market="ru",
            score=94,
            matching_reasons=["Python подходит", "Бюджет соответствует профилю"],
            user_status="interesting",
            ai_summary="Интеграционный backend-проект.",
            ai_category="automation",
            ai_technologies=["python", "telegram"],
            complexity=3,
            commercial_score=84,
            risk_flags=["Короткий срок"],
            budget_comment="Бюджет подходит",
        )

    async def set_user_status(
        self, opportunity_id: int, status: OpportunityUserStatus
    ) -> None:
        assert opportunity_id == 42
        self.saved_status = status


@pytest.mark.asyncio
async def test_opportunity_dialog_renders_details_and_saves_status() -> None:
    create_application(["it-radar-desktop-test"])
    provider = FakeDetailsProvider()
    dialog = OpportunityDialog(42, provider)

    await dialog.load()

    assert dialog.title_label.text() == "Telegram bot + CRM"
    assert dialog.score_label.text() == "94%"
    assert "Интеграционный" in dialog.ai_summary.value_label.text()
    assert "Python подходит" in dialog.matching.value_label.text()
    assert "Короткий срок" in dialog.risks.value_label.text()
    assert dialog.status_combo.currentData() == "interesting"
    assert dialog.open_button.isEnabled()

    dialog.status_combo.setCurrentIndex(dialog.status_combo.findData("responded"))
    await dialog.save_status()

    assert provider.saved_status == "responded"
    assert dialog.feedback.text() == "Статус сохранён"


def test_opportunity_dialog_rejects_non_http_source_url() -> None:
    create_application(["it-radar-desktop-test"])
    dialog = OpportunityDialog(42, FakeDetailsProvider())
    details = OpportunityDetails.model_construct(
        opportunity_id=42,
        source_url="javascript:alert(1)",
    )
    dialog.details = details

    assert dialog._source_url() is None
