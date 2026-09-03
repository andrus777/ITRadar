import os
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from app.desktop.app import create_application
from app.desktop.views import DeveloperProfileView
from app.schemas import DeveloperProfile, MatchDistribution, MatchingRecalculationResult


class FakeProfileProvider:
    def __init__(self) -> None:
        self.profile = DeveloperProfile(
            profile_id=7,
            name="Backend developer",
            technology_weights={"python": 10, "fastapi": 8},
            categories=["backend", "automation"],
            min_budget=Decimal("100000"),
            max_budget=Decimal("500000"),
            exclude_keywords=["wordpress", "gambling"],
        )

    async def load(self) -> DeveloperProfile:
        return self.profile

    async def save(self, profile: DeveloperProfile) -> DeveloperProfile:
        self.profile = profile
        return profile


class FakeMatchingProvider:
    async def distribution(self, profile_id: int) -> MatchDistribution:
        assert profile_id == 7
        return MatchDistribution(excellent=14, strong=37, possible=61, low=242)

    def recalculate(self, profile_id, progress, cancel_event):
        raise AssertionError("background execution is covered by the worker tests")


@pytest.mark.asyncio
async def test_profile_view_loads_and_saves_all_editor_fields() -> None:
    create_application(["it-radar-profile-test"])
    provider = FakeProfileProvider()
    view = DeveloperProfileView(provider, FakeMatchingProvider())

    await view.load()
    assert view.name_edit.text() == "Backend developer"
    assert view.skills.rowCount() == 2
    assert view.form_profile().technology_weights == {"fastapi": 8, "python": 10}
    assert view.distribution_labels["excellent"].text() == "90–100%\n14"

    view.name_edit.setText("Automation developer")
    view.categories_edit.setText("backend, ai")
    view.exclusions_edit.setText("crypto")
    view.min_budget.setValue(150000)
    await view.save()

    assert provider.profile.name == "Automation developer"
    assert provider.profile.categories == ["backend", "ai"]
    assert provider.profile.min_budget == Decimal("150000")
    assert provider.profile.exclude_keywords == ["crypto"]

    view._matching_complete(
        MatchingRecalculationResult(
            processed=4,
            total=4,
            cancelled=False,
            distribution=MatchDistribution(excellent=1, strong=1, possible=1, low=1),
        )
    )
    assert view.distribution_labels["low"].text() == "<70%\n1"


def test_profile_schema_rejects_invalid_weights_and_budget() -> None:
    with pytest.raises(ValueError):
        DeveloperProfile(
            profile_id=1,
            name="Invalid",
            technology_weights={"python": 11},
            min_budget=Decimal("200"),
            max_budget=Decimal("100"),
        )
