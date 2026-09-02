import os
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.ai import MockAIProvider
from app.services import AIClassifierService, OpportunityStorageService

pytestmark = pytest.mark.integration


def valid_response(*, score: int = 80) -> dict[str, object]:
    return {
        "summary": "Нужен backend-сервис",
        "category": "backend",
        "technologies": ["Python", "PostgreSQL"],
        "project_type": "development",
        "complexity": 3,
        "commercial_score": score,
        "risk_flags": ["unclear_deadline"],
        "budget_comment": "Требуется уточнение",
    }


@pytest.mark.asyncio
async def test_classifier_is_idempotent_and_persists_metadata() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection, connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)
            storage = OpportunityStorageService(session)
            source = await storage.ensure_source(
                code=f"ai-{uuid4().hex}", name="AI Test", base_url="https://example.test"
            )
            opportunity = await storage.store_opportunity(
                source_id=source.id,
                external_id="one",
                title="Разработать API",
                description="Python и PostgreSQL",
                url="https://example.test/one",
                budget_text="от 150 000 ₽",
                fingerprint="a" * 64,
            )
            provider = MockAIProvider([valid_response()], model_name="mock-v1")
            classifier = AIClassifierService(session, provider, prompt_version="prompt-v1")

            first = await classifier.classify(opportunity)
            repeated = await classifier.classify(opportunity)

            assert first.skipped is False
            assert repeated.skipped is True
            assert repeated.analysis.id == first.analysis.id
            assert provider.call_count == 1
            assert first.analysis.status == "success"
            assert first.analysis.model == "mock-v1"
            assert first.analysis.prompt_version == "prompt-v1"
            assert first.analysis.analyzed_at is not None
            assert first.analysis.commercial_score == 80

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_invalid_ai_json_does_not_stop_batch() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection, connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)
            storage = OpportunityStorageService(session)
            source = await storage.ensure_source(
                code=f"ai-batch-{uuid4().hex}",
                name="AI Batch Test",
                base_url="https://example.test",
            )
            opportunities = []
            for number in (1, 2):
                opportunities.append(
                    await storage.store_opportunity(
                        source_id=source.id,
                        external_id=str(number),
                        title=f"Заказ {number}",
                        description=None,
                        url=f"https://example.test/{number}",
                        fingerprint=str(number) * 64,
                    )
                )
            provider = MockAIProvider(["not-json", valid_response(score=90)])
            classifier = AIClassifierService(session, provider, prompt_version="prompt-v1")

            outcomes = await classifier.classify_many(opportunities)
            failed_repeated = await classifier.classify(opportunities[0])

            assert [item.analysis.status for item in outcomes] == ["failed", "success"]
            assert outcomes[0].analysis.error
            assert outcomes[1].analysis.commercial_score == 90
            assert failed_repeated.skipped is True
            assert provider.call_count == 2

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
