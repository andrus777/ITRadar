import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai import MockAIProvider
from app.collectors import FixtureCollector
from app.db.repositories import UserProfileRepository
from app.models import Match
from app.schemas import OpportunityCard, UserProfileCreate
from app.services import PipelineService

pytestmark = pytest.mark.integration
FIXTURES = Path(__file__).parents[1] / "fixtures"


class FailingCollector(FixtureCollector):
    source_code = "scheduled-failing"
    source_name = "Failing Source"

    async def fetch(self):  # type: ignore[no-untyped-def]
        raise RuntimeError("source unavailable")


class RecordingSender:
    def __init__(self) -> None:
        self.cards: list[OpportunityCard] = []

    async def send(self, card: OpportunityCard) -> None:
        self.cards.append(card)


def ai_response() -> dict[str, object]:
    return {
        "summary": "Подходящий IT-заказ",
        "category": "backend",
        "technologies": ["Python"],
        "project_type": "development",
        "complexity": 3,
        "commercial_score": 80,
        "risk_flags": [],
        "budget_comment": "Требуется уточнение",
    }


@pytest.mark.asyncio
async def test_full_pipeline_survives_source_error_and_digest_is_idempotent() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    suffix = uuid4().hex
    fixture = FixtureCollector(FIXTURES / "opportunities.json")
    fixture.source_code = f"scheduled-fixture-{suffix}"
    failing = FailingCollector(FIXTURES / "opportunities.json")
    failing.source_code = f"scheduled-failing-{suffix}"
    sender = RecordingSender()
    provider = MockAIProvider([ai_response(), ai_response()])

    try:
        async with session_factory() as session:
            profile = await UserProfileRepository(session).create(
                UserProfileCreate(name=f"Scheduled profile {suffix}")
            )
            await session.commit()
            profile_id = profile.id

        pipeline = PipelineService(
            session_factory,
            collectors={"failing": failing, "fixture": fixture},
            ai_provider=provider,
            digest_sender=sender,
            profile_id=profile_id,
            prompt_version="scheduled-v1",
            digest_min_score=70,
        )

        first = await pipeline.run()
        second = await pipeline.run()

        async with session_factory() as session:
            match_count = await session.scalar(
                select(func.count()).select_from(Match).where(Match.user_profile_id == profile_id)
            )
            unnotified_count = await session.scalar(
                select(func.count())
                .select_from(Match)
                .where(Match.user_profile_id == profile_id, Match.notified_at.is_(None))
            )

        assert first.collection_statuses["failing"] == "failed"
        assert first.collection_statuses["fixture"] == "partial_failed"
        assert first.classified_count == 2
        assert first.matched_count == 2
        assert first.notified_count == 2
        assert second.notified_count == 0
        assert provider.call_count == 2
        assert len(sender.cards) == 2
        assert match_count == 2
        assert unnotified_count == 0
    finally:
        await engine.dispose()
