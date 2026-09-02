import argparse
import asyncio
from decimal import Decimal

from app.db.repositories import UserProfileRepository
from app.db.session import async_session_factory, engine
from app.schemas import UserProfileCreate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the Telegram bot MVP profile")
    parser.add_argument("--name", required=True)
    parser.add_argument("--technologies", default="")
    parser.add_argument("--categories", default="")
    parser.add_argument("--min-budget", type=Decimal)
    parser.add_argument("--max-budget", type=Decimal)
    parser.add_argument("--exclude", default="")
    parser.add_argument("--remote-only", action="store_true")
    return parser.parse_args()


def split_terms(value: str) -> list[str]:
    return [term.strip() for term in value.split(",") if term.strip()]


async def create_profile(args: argparse.Namespace) -> int:
    async with async_session_factory() as session:
        profile = await UserProfileRepository(session).create(
            UserProfileCreate(
                name=args.name,
                technologies=split_terms(args.technologies),
                categories=split_terms(args.categories),
                min_budget=args.min_budget,
                max_budget=args.max_budget,
                exclude_keywords=split_terms(args.exclude),
                remote_only=args.remote_only,
            )
        )
        await session.commit()
        return profile.id


async def main() -> None:
    try:
        profile_id = await create_profile(parse_args())
        print(f"Created profile ID: {profile_id}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
