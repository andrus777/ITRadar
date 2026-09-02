from datetime import UTC, datetime

from app.bot.presentation import card_keyboard, render_card
from app.schemas import OpportunityCard, OpportunityPage


def page(*, budget: str | None = None, summary: str | None = None) -> OpportunityPage:
    return OpportunityPage(
        card=OpportunityCard(
            opportunity_id=1,
            title="Python <API>",
            budget=budget,
            source_name="Public & Source",
            source_url="https://example.test/jobs/1",
            summary=summary,
            score=87,
            reasons=["Совпала технология: Python"],
            published_at=datetime(2026, 9, 2, tzinfo=UTC),
        ),
        page=1,
        has_previous=True,
        has_next=True,
    )


def test_card_handles_missing_budget_and_summary_and_escapes_html() -> None:
    text = render_card(page())

    assert "Python &lt;API&gt;" in text
    assert "Бюджет:</b> не указан" in text
    assert "Краткое описание отсутствует" in text
    assert "Public &amp; Source" in text
    assert "Score:</b> 87/100" in text


def test_keyboard_uses_source_url_and_single_card_pagination() -> None:
    keyboard = card_keyboard(page(), mode="top")

    assert keyboard is not None
    assert keyboard.inline_keyboard[0][0].callback_data == "browse:top:0"
    assert keyboard.inline_keyboard[0][1].callback_data == "browse:top:2"
    assert keyboard.inline_keyboard[1][0].url == "https://example.test/jobs/1"
