import argparse
import asyncio
import json
from collections.abc import Sequence

from app.collectors import JobicyCollector
from app.db import async_session_factory
from app.services import CollectorService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an IT Radar source collector")
    subparsers = parser.add_subparsers(dest="source", required=True)
    jobicy = subparsers.add_parser("jobicy", help="Collect from the public Jobicy API")
    jobicy.add_argument("--count", type=int, default=20)
    jobicy.add_argument("--geo")
    jobicy.add_argument("--industry")
    jobicy.add_argument("--tag")
    return parser


async def run(args: argparse.Namespace) -> int:
    if args.source != "jobicy":
        raise ValueError(f"unsupported source: {args.source}")

    adapter = JobicyCollector(
        count=args.count,
        geo=args.geo,
        industry=args.industry,
        tag=args.tag,
    )
    async with async_session_factory() as session:
        result = await CollectorService(session).run(adapter)
        await session.commit()
        print(
            json.dumps(
                {
                    "run_id": result.id,
                    "status": result.status,
                    "fetched_count": result.fetched_count,
                    "new_count": result.new_count,
                    "error": result.error,
                },
                ensure_ascii=False,
            )
        )
    return 0 if result.status in {"success", "partial_failed"} else 1


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(run(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
