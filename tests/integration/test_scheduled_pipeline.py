import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai import MockAIProvider
from app.bot.presentation import card_keyboard, render_card
from app.collectors import FixtureCollector
from app.db.repositories import UserProfileRepository
from app.models import Match, Opportunity, Source
from app.schemas import OpportunityCard, OpportunityPage, UserProfileCreate
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
        self.texts: list[str] = []
        self.urls: list[str] = []

    async def send(self, card: OpportunityCard) -> None:
        self.cards.append(card)
        page = OpportunityPage(card=card, page=0, has_previous=False, has_next=False)
        self.texts.append(render_card(page))
        keyboard = card_keyboard(page, mode="top")
        assert keyboard is not None
        self.urls.append(str(keyboard.inline_keyboard[-1][0].url))


def ai_response(*, is_opportunity: bool = True) -> dict[str, object]:
    return {
        "is_opportunity": is_opportunity,
        "opportunity_probability": 0.95 if is_opportunity else 0.05,
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
async def test_fixture_e2e_collects_dedupes_matches_and_formats_digest() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    suffix = uuid4().hex
    fixture = FixtureCollector(FIXTURES / "opportunities.json")
    fixture.source_code = f"scheduled-fixture-{suffix}"
    duplicate_fixture = FixtureCollector(FIXTURES / "opportunities.json")
    duplicate_fixture.source_code = f"scheduled-duplicate-{suffix}"
    failing = FailingCollector(FIXTURES / "opportunities.json")
    failing.source_code = f"scheduled-failing-{suffix}"
    sender = RecordingSender()
    provider = MockAIProvider([ai_response(), ai_response(is_opportunity=False)])

    try:
        async with session_factory() as session:
            profile = await UserProfileRepository(session).create(
                UserProfileCreate(name=f"Scheduled profile {suffix}")
            )
            await session.commit()
            profile_id = profile.id

        pipeline = PipelineService(
            session_factory,
            collectors={
                "failing": failing,
                "fixture": fixture,
                "duplicate": duplicate_fixture,
            },
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
            duplicate_source_id = await session.scalar(
                select(Source.id).where(Source.code == duplicate_fixture.source_code)
            )
            duplicate_count = await session.scalar(
                select(func.count())
                .select_from(Opportunity)
                .where(
                    Opportunity.source_id == duplicate_source_id,
                    Opportunity.duplicate_of_id.is_not(None),
                )
            )

        assert first.collection_statuses["failing"] == "failed"
        assert first.collection_statuses["fixture"] == "partial_failed"
        assert first.collection_statuses["duplicate"] == "partial_failed"
        assert first.classified_count == 2
        assert first.matched_count == 1
        assert first.notified_count == 1
        assert second.notified_count == 0
        assert provider.call_count == 2
        assert len(sender.cards) == 1
        assert all("<b>Score:</b> 100/100" in text for text in sender.texts)
        assert all("Подходящий IT-заказ" in text for text in sender.texts)
        assert sender.urls == [card.source_url for card in sender.cards]
        assert match_count == 1
        assert unnotified_count == 0
        assert duplicate_count == 2
    finally:
        await engine.dispose()
