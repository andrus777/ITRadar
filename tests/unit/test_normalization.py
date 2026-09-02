from datetime import UTC, datetime
from decimal import Decimal

from app.schemas import NormalizedOpportunity
from app.services.normalization import (
    OpportunityNormalizationService,
    normalize_url,
    parse_budget,
)


def test_parse_budget_range_in_thousands_of_rubles() -> None:
    budget = parse_budget("100–300 тыс. ₽")

    assert budget.minimum == Decimal(100_000)
    assert budget.maximum == Decimal(300_000)
    assert budget.currency == "RUB"
    assert budget.negotiable is False


def test_parse_budget_from_value_without_currency() -> None:
    budget = parse_budget("от 150 000")

    assert budget.minimum == Decimal(150_000)
    assert budget.maximum is None
    assert budget.currency is None


def test_parse_negotiable_budget() -> None:
    budget = parse_budget("договорная")

    assert budget.minimum is None
    assert budget.maximum is None
    assert budget.negotiable is True
    assert budget.text == "negotiable"


def test_normalize_url_removes_tracking_and_cosmetic_differences() -> None:
    first = normalize_url("HTTPS://www.Example.com/jobs/42/?utm_source=feed&b=2&a=1#top")
    second = normalize_url("https://example.com/jobs/42?a=1&b=2")

    assert first == second == "https://example.com/jobs/42?a=1&b=2"


def test_normalizer_cleans_html_whitespace_and_rebuilds_fingerprint() -> None:
    opportunity = NormalizedOpportunity(
        external_id="one",
        title="  Python   API  ",
        description="<p>Build&nbsp;an <strong>API</strong></p>",
        url="https://www.example.com/jobs/one/?utm_campaign=test",
        budget_text="100–300 тыс. ₽",
        fetched_at=datetime.now(UTC),
        fingerprint="0" * 64,
    )

    normalized = OpportunityNormalizationService().normalize(opportunity)

    assert normalized.title == "Python API"
    assert normalized.description == "Build an API"
    assert normalized.normalized_title == "python api"
    assert normalized.normalized_url == "https://example.com/jobs/one"
    assert normalized.budget_from == Decimal(100_000)
    assert normalized.budget_to == Decimal(300_000)
    assert normalized.fingerprint != "0" * 64
