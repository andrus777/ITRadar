import os
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.repositories import MatchRepository, PipelineRepository, UserProfileRepository
from app.schemas import MatchResult, UserProfileCreate
from app.services import OpportunityStorageService

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_digest_excludes_international_unless_explicitly_enabled() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection, connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)
            suffix = uuid4().hex
            storage = OpportunityStorageService(session)
            source = await storage.ensure_source(
                code=f"digest-market-{suffix}",
                name="Digest market test",
                base_url="https://example.test",
            )
            russian = await storage.store_opportunity(
                source_id=source.id,
                external_id="ru",
                title="Russian project",
                url="https://example.test/ru",
                market="ru",
                fingerprint="1" * 64,
            )
            international = await storage.store_opportunity(
                source_id=source.id,
                external_id="international",
                title="International vacancy",
                url="https://example.test/international",
                market="international",
                opportunity_type="vacancy",
                fingerprint="2" * 64,
            )
            profile = await UserProfileRepository(session).create(
                UserProfileCreate(name=f"Digest market {suffix}")
            )
            matches = MatchRepository(session)
            result = MatchResult(score=90, reasons=[])
            await matches.upsert(
                user_profile_id=profile.id, opportunity_id=russian.id, result=result
            )
            await matches.upsert(
                user_profile_id=profile.id, opportunity_id=international.id, result=result
            )
            repository = PipelineRepository(session)

            default_digest = await repository.pending_digest(
                profile_id=profile.id, min_score=70, limit=20
            )
            full_digest = await repository.pending_digest(
                profile_id=profile.id,
                min_score=70,
                limit=20,
                include_international=True,
            )

            assert [item.card.title for item in default_digest] == ["Russian project"]
            assert {item.card.title for item in full_digest} == {
                "Russian project",
                "International vacancy",
            }

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
