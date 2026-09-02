import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.repositories import MatchRepository, UserProfileRepository
from app.schemas import MatchReason, MatchResult, UserProfileCreate
from app.services import OpportunityBrowserService, OpportunityStorageService

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_top_is_score_sorted_and_latest_handles_missing_optional_fields() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection, connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)
            storage = OpportunityStorageService(session)
            source = await storage.ensure_source(
                code=f"browser-{uuid4().hex}",
                name="Browser Source",
                base_url="https://example.test",
            )
            older = await storage.store_opportunity(
                source_id=source.id,
                external_id="older",
                title="High score",
                description=None,
                url="https://example.test/high",
                budget_text=None,
                published_at=datetime.now(UTC) - timedelta(days=1),
                fingerprint="e" * 64,
            )
            newer = await storage.store_opportunity(
                source_id=source.id,
                external_id="newer",
                title="Latest",
                description=None,
                url="https://example.test/latest",
                budget_text=None,
                published_at=datetime.now(UTC),
                fingerprint="f" * 64,
            )
            profile = await UserProfileRepository(session).create(UserProfileCreate(name="MVP"))
            matches = MatchRepository(session)
            reason = MatchReason(factor="technologies", matched=True, points=35, message="Подходит")
            await matches.upsert(
                user_profile_id=profile.id,
                opportunity_id=older.id,
                result=MatchResult(score=95, reasons=[reason]),
            )
            await matches.upsert(
                user_profile_id=profile.id,
                opportunity_id=newer.id,
                result=MatchResult(score=50, reasons=[reason]),
            )
            browser = OpportunityBrowserService(session, profile_id=profile.id)

            top = await browser.top()
            latest = await browser.latest()

            assert top.card is not None
            assert top.card.title == "High score"
            assert top.card.score == 95
            assert top.card.source_url == "https://example.test/high"
            assert top.has_next is True
            assert latest.card is not None
            assert latest.card.title == "Latest"
            assert latest.card.budget is None
            assert latest.card.summary is None

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
