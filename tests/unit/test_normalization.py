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
    assert budget.budget_type == "fixed"


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
    assert budget.budget_type == "negotiable"
    assert budget.text == "negotiable"


def test_parse_freelance_ru_negotiable_budget() -> None:
    budget = parse_budget("Обсуждается индивидуально")

    assert budget.budget_type == "negotiable"
    assert budget.negotiable is True


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
        source_category="Веб-разработка и IT",
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
    assert normalized.budget_type == "fixed"
    assert normalized.category == "api"
    assert normalized.technologies == ["python"]
    assert normalized.customer_type == "unknown"
    assert normalized.content_hash != "0" * 64
    assert normalized.fingerprint != "0" * 64


def test_content_hash_includes_normalized_budget() -> None:
    service = OpportunityNormalizationService()
    common = {
        "external_id": "hash",
        "title": "Python API",
        "description": "CRM integration",
        "url": "https://example.com/hash",
        "fetched_at": datetime.now(UTC),
        "fingerprint": "0" * 64,
    }

    first = service.normalize(NormalizedOpportunity(**common, budget_text="100–200 тыс. ₽"))
    same = service.normalize(NormalizedOpportunity(**common, budget_text="100000-200000 RUB"))
    changed = service.normalize(NormalizedOpportunity(**common, budget_text="от 300 000 ₽"))

    assert first.content_hash == same.content_hash
    assert first.content_hash != changed.content_hash
    assert first.fingerprint == changed.fingerprint


def test_normalizer_distinguishes_category_technologies_and_customer_type() -> None:
    opportunity = NormalizedOpportunity(
        external_id="two",
        title="Telegram-бот на Python и FastAPI",
        description="Заказчик — компания, интеграция с PostgreSQL",
        url="https://example.com/two",
        budget_text="2 000 ₽ / час",
        fetched_at=datetime.now(UTC),
        opportunity_type="freelance",
        market="ru",
        fingerprint="0" * 64,
    )

    normalized = OpportunityNormalizationService().normalize(opportunity)

    assert normalized.opportunity_type == "freelance"
    assert normalized.market == "ru"
    assert normalized.category == "telegram"
    assert normalized.technologies == ["fastapi", "postgresql", "python", "telegram"]
    assert normalized.budget_type == "hourly"
    assert normalized.customer_type == "business"


def test_normalizer_detects_monthly_and_government_customer() -> None:
    opportunity = NormalizedOpportunity(
        external_id="three",
        title="Администрирование инфраструктуры",
        description="Проект для государственного учреждения",
        url="https://example.com/three",
        budget_text="150 000 ₽ в месяц",
        fetched_at=datetime.now(UTC),
        fingerprint="0" * 64,
    )

    normalized = OpportunityNormalizationService().normalize(opportunity)

    assert normalized.category == "infrastructure"
    assert normalized.budget_type == "monthly"
    assert normalized.customer_type == "government"
