import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.repositories import UserProfileRepository
from app.db.session import async_session_factory, engine
from app.schemas import UserProfileCreate

DEMO_PROFILE_NAME = "Demo Python Developer"


async def seed_demo_profile(
    session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
) -> int:
    async with session_factory() as session:
        repository = UserProfileRepository(session)
        profile = await repository.get_by_name(DEMO_PROFILE_NAME)
        if profile is None:
            profile = await repository.create(
                UserProfileCreate(
                    name=DEMO_PROFILE_NAME,
                    technologies=["python", "fastapi", "postgresql", "docker"],
                    categories=["backend", "data engineering", "automation"],
                    min_budget=None,
                    max_budget=None,
                    exclude_keywords=["wordpress", "unpaid", "equity only"],
                    remote_only=True,
                )
            )
        await session.commit()
        return profile.id


async def main() -> None:
    try:
        profile_id = await seed_demo_profile()
        print(f"Demo profile ID: {profile_id}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
