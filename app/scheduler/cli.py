import argparse
import asyncio
import json
import logging
from dataclasses import asdict

from app.db.session import engine
from app.logging import configure_logging
from app.scheduler.runtime import build_runtime
from app.scheduler.service import SchedulerService
from app.settings import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or schedule the complete IT Radar pipeline")
    parser.add_argument("command", choices=("run", "schedule"), nargs="?", default="run")
    return parser.parse_args()


async def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    runtime = build_runtime(settings)
    scheduler = SchedulerService(
        runtime.pipeline,
        cron=settings.scheduler_cron,
        timezone=settings.scheduler_timezone,
    )
    try:
        if parse_args().command == "run":
            report = await scheduler.run_once()
            logger.info("manual pipeline finished", extra=asdict(report))
            print(json.dumps(asdict(report), ensure_ascii=False))
            return 0 if not report.errors else 1
        if not settings.scheduler_enabled:
            raise RuntimeError("scheduler is disabled by IT_RADAR_SCHEDULER_ENABLED")
        scheduler.start()
        logger.info(
            "scheduler started",
            extra={"cron": settings.scheduler_cron, "timezone": settings.scheduler_timezone},
        )
        print(f"Scheduler started: {settings.scheduler_cron} ({settings.scheduler_timezone})")
        await asyncio.Event().wait()
        return 0
    finally:
        scheduler.shutdown()
        await runtime.close()
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
