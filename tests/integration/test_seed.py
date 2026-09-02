import os

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import UserProfile
from app.seed import DEMO_PROFILE_NAME, seed_demo_profile

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_demo_profile_seed_is_idempotent() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        first_id = await seed_demo_profile(session_factory)
        second_id = await seed_demo_profile(session_factory)
        async with engine.connect() as connection:
            count = await connection.scalar(
                select(func.count())
                .select_from(UserProfile)
                .where(UserProfile.name == DEMO_PROFILE_NAME)
            )
        assert second_id == first_id
        assert count == 1
    finally:
        await engine.dispose()
