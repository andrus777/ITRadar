from decimal import Decimal

from app.models import AIAnalysis, Opportunity, UserProfile
from app.services import MatchingEngine


def profile(**overrides: object) -> UserProfile:
    values = {
        "id": 1,
        "name": "Backend developer",
        "technologies": ["python"],
        "categories": ["backend"],
        "min_budget": Decimal("100000"),
        "max_budget": Decimal("300000"),
        "exclude_keywords": ["wordpress"],
        "remote_only": True,
    }
    return UserProfile(**(values | overrides))


def opportunity(**overrides: object) -> Opportunity:
    values = {
        "id": 1,
        "source_id": 1,
        "external_id": "job-1",
        "title": "Python API",
        "description": "Backend service",
        "url": "https://example.test/job-1",
        "budget_from": Decimal("150000"),
        "budget_to": Decimal("250000"),
        "remote": True,
        "fingerprint": "a" * 64,
    }
    return Opportunity(**(values | overrides))


def analysis(**overrides: object) -> AIAnalysis:
    values = {
        "id": 1,
        "opportunity_id": 1,
        "status": "success",
        "summary": "Backend API",
        "category": "backend",
        "technologies": ["Python", "FastAPI"],
        "model": "mock",
        "prompt_version": "v1",
        "input_hash": "b" * 64,
    }
    return AIAnalysis(**(values | overrides))


def test_same_inputs_produce_same_full_score() -> None:
    engine = MatchingEngine()

    first = engine.calculate(profile(), opportunity(), analysis())
    second = engine.calculate(profile(), opportunity(), analysis())

    assert first == second
    assert first.score == 100
    assert [reason.factor for reason in first.reasons] == [
        "technologies",
        "category",
        "budget",
        "remote",
    ]


def test_budget_outside_profile_loses_budget_points() -> None:
    result = MatchingEngine().calculate(
        profile(),
        opportunity(budget_from=Decimal("400000"), budget_to=Decimal("500000")),
        analysis(),
    )

    budget = next(reason for reason in result.reasons if reason.factor == "budget")
    assert result.score == 75
    assert budget.matched is False
    assert "вне диапазона" in budget.message


def test_open_ended_budget_from_overlaps_profile() -> None:
    result = MatchingEngine().calculate(
        profile(min_budget=Decimal("200000"), max_budget=Decimal("300000")),
        opportunity(budget_from=Decimal("150000"), budget_to=None),
        analysis(),
    )

    budget = next(reason for reason in result.reasons if reason.factor == "budget")
    assert budget.matched is True
    assert budget.points == MatchingEngine.BUDGET_POINTS


def test_open_ended_budget_up_to_overlaps_profile() -> None:
    result = MatchingEngine().calculate(
        profile(min_budget=Decimal("100000"), max_budget=Decimal("200000")),
        opportunity(budget_from=None, budget_to=Decimal("150000")),
        analysis(),
    )

    budget = next(reason for reason in result.reasons if reason.factor == "budget")
    assert budget.matched is True
    assert budget.points == MatchingEngine.BUDGET_POINTS


def test_blacklist_forces_zero_score() -> None:
    result = MatchingEngine().calculate(
        profile(), opportunity(description="Доработка WordPress сайта"), analysis()
    )

    assert result.score == 0
    assert result.reasons[0].factor == "blacklist"
    assert "wordpress" in result.reasons[0].message


def test_missing_technology_and_non_remote_are_scored_separately() -> None:
    result = MatchingEngine().calculate(
        profile(), opportunity(remote=False), analysis(technologies=["Java"])
    )

    assert result.score == 45
    technology = next(reason for reason in result.reasons if reason.factor == "technologies")
    remote = next(reason for reason in result.reasons if reason.factor == "remote")
    assert technology.matched is False
    assert remote.matched is False
