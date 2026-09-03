import os
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from app.desktop.app import create_application
from app.desktop.views import DeveloperProfileView
from app.schemas import DeveloperProfile


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


@pytest.mark.asyncio
async def test_profile_view_loads_and_saves_all_editor_fields() -> None:
    create_application(["it-radar-profile-test"])
    provider = FakeProfileProvider()
    view = DeveloperProfileView(provider)

    await view.load()
    assert view.name_edit.text() == "Backend developer"
    assert view.skills.rowCount() == 2
    assert view.form_profile().technology_weights == {"fastapi": 8, "python": 10}

    view.name_edit.setText("Automation developer")
    view.categories_edit.setText("backend, ai")
    view.exclusions_edit.setText("crypto")
    view.min_budget.setValue(150000)
    await view.save()

    assert provider.profile.name == "Automation developer"
    assert provider.profile.categories == ["backend", "ai"]
    assert provider.profile.min_budget == Decimal("150000")
    assert provider.profile.exclude_keywords == ["crypto"]


def test_profile_schema_rejects_invalid_weights_and_budget() -> None:
    with pytest.raises(ValueError):
        DeveloperProfile(
            profile_id=1,
            name="Invalid",
            technology_weights={"python": 11},
            min_budget=Decimal("200"),
            max_budget=Decimal("100"),
        )
