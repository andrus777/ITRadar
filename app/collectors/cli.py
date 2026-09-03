import argparse
import asyncio
import json
from collections.abc import Sequence

from app.collectors.b2b_center import B2BCenterCollector
from app.collectors.fl_ru import FLRuCollector
from app.collectors.freelance_ru import FreelanceRuCollector
from app.collectors.jobicy import JobicyCollector
from app.collectors.registry import configured_collectors
from app.collectors.remoteok import RemoteOKCollector
from app.collectors.telegram import TelegramChannelCollector
from app.collectors.weworkremotely import WeWorkRemotelyCollector
from app.collectors.workspace import WorkspaceCollector
from app.db import async_session_factory
from app.services import CollectorService
from app.settings import get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an IT Radar source collector")
    subparsers = parser.add_subparsers(dest="source", required=True)
    b2b_center = subparsers.add_parser(
        "b2b_center", help="Collect public Russian software tenders from B2B-Center"
    )
    b2b_center.add_argument("--count", type=int, default=50)
    fl_ru = subparsers.add_parser("fl_ru", help="Collect Russian IT projects from FL.ru RSS")
    fl_ru.add_argument("--count", type=int, default=50)
    freelance_ru = subparsers.add_parser(
        "freelance_ru", help="Collect public Web/IT and AI tasks from Freelance.ru"
    )
    freelance_ru.add_argument("--count", type=int, default=50)
    jobicy = subparsers.add_parser("jobicy", help="Collect from the public Jobicy API")
    jobicy.add_argument("--count", type=int, default=20)
    jobicy.add_argument("--geo")
    jobicy.add_argument("--industry")
    jobicy.add_argument("--tag")
    remoteok = subparsers.add_parser("remoteok", help="Collect from Remote OK JSON")
    remoteok.add_argument("--count", type=int, default=20)
    remoteok.add_argument("--tag")
    weworkremotely = subparsers.add_parser(
        "weworkremotely", help="Collect from We Work Remotely RSS"
    )
    weworkremotely.add_argument("--count", type=int, default=20)
    workspace = subparsers.add_parser("workspace", help="Collect public Workspace tenders")
    workspace.add_argument("--count", type=int, default=50)
    telegram = subparsers.add_parser(
        "telegram", help="Collect all enabled public Telegram whitelist channels"
    )
    telegram.add_argument("--count", type=int, default=20)
    subparsers.add_parser("all", help="Run every enabled collector")
    return parser


async def run(args: argparse.Namespace) -> int:
    collectors = configured_collectors(get_settings())
    if args.source == "all":
        selected = collectors
    elif args.source == "telegram":
        selected = {
            name: adapter
            for name, adapter in collectors.items()
            if isinstance(adapter, TelegramChannelCollector)
        }
        for adapter in selected.values():
            adapter.count = args.count
        if not selected:
            print(json.dumps({"source": "telegram", "status": "disabled"}))
            return 2
    else:
        if args.source not in collectors:
            print(json.dumps({"source": args.source, "status": "disabled"}))
            return 2
        adapter = collectors[args.source]
        adapter.count = args.count
        if isinstance(adapter, (JobicyCollector, RemoteOKCollector)):
            adapter.tag = args.tag
        if isinstance(adapter, JobicyCollector):
            adapter.geo = args.geo
            adapter.industry = args.industry
        if not isinstance(
            adapter,
            (
                FLRuCollector,
                B2BCenterCollector,
                FreelanceRuCollector,
                JobicyCollector,
                RemoteOKCollector,
                TelegramChannelCollector,
                WeWorkRemotelyCollector,
                WorkspaceCollector,
            ),
        ):
            raise TypeError(f"unsupported configured collector: {type(adapter).__name__}")
        selected = {args.source: adapter}

    results: list[dict[str, object]] = []
    async with async_session_factory() as session:
        for source_name, adapter in selected.items():
            result = await CollectorService(session).run(adapter)
            await session.commit()
            results.append(
                {
                    "source": source_name,
                    "run_id": result.id,
                    "status": result.status,
                    "fetched_count": result.fetched_count,
                    "new_count": result.new_count,
                    "duplicate_count": result.duplicate_count,
                    "rejected_count": result.rejected_count,
                    "error": result.error,
                }
            )
    print(json.dumps(results, ensure_ascii=False))
    return 0 if all(item["status"] in {"success", "partial_failed"} for item in results) else 1


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(run(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
