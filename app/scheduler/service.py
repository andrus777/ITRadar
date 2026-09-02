from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services import PipelineReport, PipelineService


class SchedulerService:
    def __init__(
        self,
        pipeline: PipelineService,
        *,
        cron: str,
        timezone: str,
    ) -> None:
        self.pipeline = pipeline
        self.scheduler = AsyncIOScheduler(timezone=timezone)
        self.trigger = CronTrigger.from_crontab(cron, timezone=timezone)

    async def run_once(self) -> PipelineReport:
        return await self.pipeline.run()

    def start(self) -> None:
        self.scheduler.add_job(
            self.pipeline.run,
            trigger=self.trigger,
            id="daily-it-radar-pipeline",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=3600,
        )
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
