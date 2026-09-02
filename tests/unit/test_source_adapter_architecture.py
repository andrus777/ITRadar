from app.collectors import BaseSourceAdapter, FixtureCollector
from app.models import CollectionRun, SourceRun
from app.schemas import CollectedItem, NormalizedOpportunity


def test_existing_adapters_use_unified_parse_contract() -> None:
    item = CollectedItem(
        external_id="1",
        url="https://example.test/1",
        payload={"title": "Example"},
    )

    assert issubclass(FixtureCollector, BaseSourceAdapter)
    assert FixtureCollector.parse(FixtureCollector.__new__(FixtureCollector), item) is item


def test_source_run_keeps_collection_run_compatibility() -> None:
    run = SourceRun(fetched_count=3, new_count=2)

    assert CollectionRun is SourceRun
    assert run.items_received == 3
    assert run.items_new == 2


def test_opportunity_schema_defaults_new_classification_fields() -> None:
    opportunity = NormalizedOpportunity(
        external_id="1",
        title="Example",
        url="https://example.test/1",
        fetched_at=CollectedItem(
            external_id="1", url="https://example.test/1", payload={}
        ).fetched_at,
        fingerprint="a" * 64,
    )

    assert opportunity.opportunity_type == "unknown"
    assert opportunity.market == "unknown"
