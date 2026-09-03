import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.repositories import MatchRepository, UserProfileRepository
from app.schemas import MatchReason, MatchResult, UserProfileCreate
from app.schemas.opportunity_management import OpportunityFilters
from app.services import OpportunityManagementService, OpportunityStorageService

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_opportunity_search_filters_and_sorts_in_repository() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection, connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)
            storage = OpportunityStorageService(session)
            suffix = uuid4().hex
            source = await storage.ensure_source(
                code=f"opportunities-{suffix}",
                name="Opportunity Source",
                base_url="https://example.test",
            )
            python_opportunity = await storage.store_opportunity(
                source_id=source.id,
                external_id="python",
                title="Python API integration",
                description="FastAPI and PostgreSQL",
                url="https://example.test/python",
                market="ru",
                opportunity_type="project",
                category="backend",
                technologies=["python", "fastapi", "postgresql"],
                budget_from=Decimal("150000"),
                budget_to=Decimal("250000"),
                budget_text="150–250 тыс. ₽",
                published_at=datetime.now(UTC),
                fingerprint="1" * 64,
                content_hash="2" * 64,
            )
            other_opportunity = await storage.store_opportunity(
                source_id=source.id,
                external_id="frontend",
                title="React landing page",
                description="Frontend",
                url="https://example.test/frontend",
                market="international",
                opportunity_type="freelance",
                category="frontend",
                technologies=["react"],
                budget_from=Decimal("50000"),
                budget_text="$500",
                published_at=datetime.now(UTC) - timedelta(days=10),
                fingerprint="3" * 64,
                content_hash="4" * 64,
            )
            profile = await UserProfileRepository(session).create(
                UserProfileCreate(name=f"Opportunities {suffix}")
            )
            matches = MatchRepository(session)
            reason = MatchReason(
                factor="technologies",
                matched=True,
                points=35,
                message="technology match",
            )
            await matches.upsert(
                user_profile_id=profile.id,
                opportunity_id=python_opportunity.id,
                result=MatchResult(score=92, reasons=[reason]),
            )
            await matches.upsert(
                user_profile_id=profile.id,
                opportunity_id=other_opportunity.id,
                result=MatchResult(score=75, reasons=[reason]),
            )
            service = OpportunityManagementService(session, profile_id=profile.id)

            page = await service.search(
                OpportunityFilters(
                    search="API",
                    market="ru",
                    opportunity_type="project",
                    category="backend",
                    technology="python",
                    budget_from=Decimal("100000"),
                    budget_to=Decimal("300000"),
                    score_from=80,
                    published_days=3,
                    sort_by="score",
                )
            )
            sources, categories = await service.filter_values()

            assert page.total == 1
            assert page.items[0].opportunity_id == python_opportunity.id
            assert page.items[0].score == 92
            assert (source.code, source.name) in sources
            assert {"backend", "frontend"}.issubset(categories)

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
