import os
from datetime import UTC, datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from app.desktop.app import create_application
from app.desktop.views import OpportunitiesView
from app.schemas.opportunity_management import (
    OpportunityFilters,
    OpportunityListItem,
    OpportunityListPage,
)


class FakeOpportunityProvider:
    def __init__(self) -> None:
        self.filters: OpportunityFilters | None = None

    async def filter_values(self) -> tuple[list[tuple[str, str]], list[str]]:
        return [("fl_ru", "FL.ru")], ["backend"]

    async def search(self, filters: OpportunityFilters) -> OpportunityListPage:
        self.filters = filters
        return OpportunityListPage(
            items=[
                OpportunityListItem(
                    opportunity_id=7,
                    score=91,
                    title="Python API",
                    source="FL.ru",
                    source_code="fl_ru",
                    opportunity_type="project",
                    market="ru",
                    category="backend",
                    technologies=["python", "fastapi"],
                    budget="150 000 ₽",
                    published_at=datetime(2026, 9, 3, 10, 0, tzinfo=UTC),
                    status="active",
                )
            ],
            total=26,
            page=filters.page,
            page_size=25,
            total_pages=2,
        )


@pytest.mark.asyncio
async def test_opportunities_view_loads_filters_table_and_pagination() -> None:
    create_application(["it-radar-desktop-test"])
    provider = FakeOpportunityProvider()
    view = OpportunitiesView(provider)

    await view.load(initial=True)

    assert view.source_combo.count() == 2
    assert view.category_combo.count() == 2
    assert view.model.rowCount() == 1
    assert view.model.index(0, 0).data() == "91%"
    assert view.model.index(0, 1).data() == "Python API"
    assert view.result_label.text() == "Найдено: 26"
    assert view.next_button.isEnabled()


def test_opportunities_view_builds_complete_filter_contract() -> None:
    create_application(["it-radar-desktop-test"])
    view = OpportunitiesView(FakeOpportunityProvider())
    view.search_edit.setText("Python")
    view.market_combo.setCurrentIndex(1)
    view.technology_edit.setText("FastAPI")
    view.budget_from.setValue(100_000)
    view.score_from.setValue(80)

    filters = view._filters()

    assert filters.search == "Python"
    assert filters.market == "ru"
    assert filters.technology == "FastAPI"
    assert filters.budget_from == 100_000
    assert filters.score_from == 80
