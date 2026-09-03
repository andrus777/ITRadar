import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.repositories import UserProfileRepository
from app.models import AIAnalysis, Match
from app.schemas import DeveloperProfile, UserProfileCreate
from app.services import MatchingEngine, OpportunityStorageService
from app.services.developer_profile import DeveloperProfileService

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_match_score_and_reasons_are_upserted() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection, connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)
            storage = OpportunityStorageService(session)
            source = await storage.ensure_source(
                code=f"match-{uuid4().hex}", name="Match Test", base_url="https://example.test"
            )
            opportunity = await storage.store_opportunity(
                source_id=source.id,
                external_id="one",
                title="Python API",
                description="Backend service",
                url="https://example.test/one",
                budget_from=Decimal("150000"),
                budget_to=Decimal("250000"),
                remote=True,
                fingerprint="c" * 64,
            )
            profile = await UserProfileRepository(session).create(
                UserProfileCreate(
                    name="Python developer",
                    technologies=[" Python "],
                    technology_weights={" Python ": 10},
                    categories=["BACKEND"],
                    min_budget=Decimal("100000"),
                    remote_only=True,
                )
            )
            analysis = AIAnalysis(
                opportunity_id=opportunity.id,
                status="success",
                summary="Backend API",
                category="backend",
                technologies=["Python"],
                model="mock",
                prompt_version="v1",
                input_hash="d" * 64,
            )
            session.add(analysis)
            await session.flush()
            matching = MatchingEngine(session)

            first = await matching.calculate_and_store(profile, opportunity, analysis)
            first_matched_at = first.matched_at
            analysis.technologies = ["Java"]
            repeated = await matching.calculate_and_store(profile, opportunity, analysis)
            count = await session.scalar(select(func.count()).select_from(Match))

            assert repeated.score == 65
            assert profile.technology_weights == {"python": 10}
            assert repeated.id == first.id
            assert count == 1
            assert repeated.reasons[0]["factor"] == "technologies"
            assert "не найдены" in repeated.reasons[0]["message"]
            assert repeated.matched_at > first_matched_at

            updated = await DeveloperProfileService(session).save(
                DeveloperProfile(
                    profile_id=profile.id,
                    name="Updated developer",
                    technology_weights={"FastAPI": 9},
                    categories=["Automation"],
                    min_budget=Decimal("120000"),
                    max_budget=Decimal("400000"),
                    exclude_keywords=["Crypto"],
                )
            )
            assert updated.technology_weights == {"fastapi": 9}
            assert profile.technologies == ["fastapi"]

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
