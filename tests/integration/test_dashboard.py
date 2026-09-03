import os
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.repositories import MatchRepository, UserProfileRepository
from app.schemas import MatchReason, MatchResult, UserProfileCreate
from app.services import DashboardService, OpportunityStorageService

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_dashboard_loads_kpis_and_score_sorted_opportunities() -> None:
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
                code=f"dashboard-{suffix}",
                name="Dashboard Source",
                base_url="https://example.test",
            )
            opportunity = await storage.store_opportunity(
                source_id=source.id,
                external_id="top",
                title="Dashboard opportunity",
                description="Python integration",
                url="https://example.test/top",
                budget_from=Decimal("150000"),
                budget_to=Decimal("250000"),
                budget_text="150–250 тыс. ₽",
                opportunity_type="project",
                published_at=datetime.now(UTC),
                fingerprint="d" * 64,
                content_hash="e" * 64,
            )
            profile = await UserProfileRepository(session).create(
                UserProfileCreate(name=f"Dashboard {suffix}")
            )
            await MatchRepository(session).upsert(
                user_profile_id=profile.id,
                opportunity_id=opportunity.id,
                result=MatchResult(
                    score=94,
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

            snapshot = await DashboardService(session).snapshot(
                profile_id=profile.id,
                ai_enabled=True,
                telegram_enabled=False,
            )

            metrics = {item.key: item.value for item in snapshot.metrics}
            assert int(metrics["new"]) >= 1
            assert metrics["matched"] == "1"
            assert snapshot.opportunities[0].opportunity_id == opportunity.id
            assert snapshot.opportunities[0].score == 94
            assert snapshot.opportunities[0].source == "Dashboard Source"

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
