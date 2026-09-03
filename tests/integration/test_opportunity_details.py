import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.repositories import AIAnalysisRepository, MatchRepository, UserProfileRepository
from app.schemas import AIAnalysisResponse, MatchReason, MatchResult, UserProfileCreate
from app.schemas.opportunity_management import OpportunityFilters
from app.services import (
    OpportunityDetailsService,
    OpportunityManagementService,
    OpportunityStorageService,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_details_and_profile_specific_status_round_trip() -> None:
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
                code=f"details-{suffix}",
                name="Details Source",
                base_url="https://example.test",
            )
            opportunity = await storage.store_opportunity(
                source_id=source.id,
                external_id="details",
                title="Python CRM integration",
                description="Build a Telegram integration",
                url="https://example.test/details",
                category="backend",
                technologies=["python", "telegram"],
                budget_text="200 000 ₽",
                customer_name="Customer",
                opportunity_type="project",
                market="ru",
                published_at=datetime.now(UTC),
                fingerprint="5" * 64,
                content_hash="6" * 64,
            )
            profile = await UserProfileRepository(session).create(
                UserProfileCreate(name=f"Details {suffix}")
            )
            await MatchRepository(session).upsert(
                user_profile_id=profile.id,
                opportunity_id=opportunity.id,
                result=MatchResult(
                    score=93,
                    reasons=[
                        MatchReason(
                            factor="technologies",
                            matched=True,
                            points=35,
                            message="Python подходит",
                        )
                    ],
                ),
            )
            await AIAnalysisRepository(session).create_success(
                opportunity_id=opportunity.id,
                model="mock",
                prompt_version="v1",
                input_hash=opportunity.content_hash,
                result=AIAnalysisResponse(
                    is_opportunity=True,
                    opportunity_probability=0.98,
                    summary="CRM integration project",
                    category="automation",
                    technologies=["python", "telegram"],
                    project_type="project",
                    complexity=3,
                    commercial_score=88,
                    risk_flags=["deadline"],
                    budget_comment="budget is suitable",
                ),
            )
            details_service = OpportunityDetailsService(session, profile_id=profile.id)

            before = await details_service.get(opportunity.id)
            await details_service.set_user_status(opportunity.id, "responded")
            after = await details_service.get(opportunity.id)
            filtered = await OpportunityManagementService(
                session, profile_id=profile.id
            ).search(OpportunityFilters(status="responded"))

            assert before is not None and before.user_status == "new"
            assert after is not None and after.user_status == "responded"
            assert after.ai_summary == "CRM integration project"
            assert after.score == 93
            assert after.matching_reasons == ["Python подходит"]
            assert filtered.total == 1
            assert filtered.items[0].status == "responded"

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
