from unittest.mock import AsyncMock

import pytest

from app.scheduler import SchedulerService
from app.services import PipelineReport


@pytest.mark.asyncio
async def test_scheduler_run_once_delegates_to_complete_pipeline() -> None:
    pipeline = AsyncMock()
    pipeline.run.return_value = PipelineReport(notified_count=3)
    scheduler = SchedulerService(pipeline, cron="0 9 * * *", timezone="Europe/Moscow")

    report = await scheduler.run_once()

    assert report.notified_count == 3
    pipeline.run.assert_awaited_once()
    assert (
        str(scheduler.trigger) == "cron[month='*', day='*', day_of_week='*', hour='9', minute='0']"
    )
