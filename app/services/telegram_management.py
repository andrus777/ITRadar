from datetime import UTC, datetime

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import (
    PipelineRepository,
    TelegramManagementRepository,
    UserProfileRepository,
)
from app.schemas import (
    OpportunityCard,
    TelegramConfiguration,
    TelegramOverview,
)
from app.services.digest import DigestSender, DigestService
from app.services.opportunity_browser import OpportunityBrowserService
from app.settings import Settings


class TelegramManagementService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repository = TelegramManagementRepository(session)
        self.pipeline = PipelineRepository(session)
        self.profiles = UserProfileRepository(session)

    async def overview(self) -> TelegramOverview:
        configuration = await self.configuration()
        profile_id = await self.profile_id()
        return TelegramOverview(
            configured=self.settings.telegram_bot_token is not None,
            token_mask=self._token_mask(),
            configuration=configuration,
            last_digest_at=await self.repository.last_digest_at(profile_id),
            next_digest_at=self._next_digest(),
        )

    async def configuration(self) -> TelegramConfiguration:
        row = await self.repository.settings()
        if row is None:
            configuration = TelegramConfiguration(
                enabled=self.settings.telegram_bot_token is not None,
                chat_id=self.settings.telegram_digest_chat_id,
                min_score=self.settings.digest_min_score,
                min_budget=None,
                max_items=self.settings.digest_batch_size,
                include_international=self.settings.include_international,
                include_types=[],
            )
            row = await self.repository.create(configuration)
        return self._configuration(row)

    async def save(self, configuration: TelegramConfiguration) -> TelegramOverview:
        configuration = configuration.model_copy(
            update={
                "include_types": sorted(
                    {
                        value.strip().casefold()
                        for value in configuration.include_types
                        if value.strip()
                    }
                )
            }
        )
        row = await self.repository.settings()
        if row is None:
            await self.repository.create(configuration)
        else:
            await self.repository.update(row, configuration)
        return await self.overview()

    async def preview(self, configuration: TelegramConfiguration) -> list[OpportunityCard]:
        pending = await self.pipeline.pending_digest(
            profile_id=await self.profile_id(),
            min_score=configuration.min_score,
            limit=configuration.max_items,
            include_international=configuration.include_international,
            min_budget=configuration.min_budget,
            include_types=configuration.include_types,
        )
        return [OpportunityBrowserService.card_from_row(item.card) for item in pending]

    async def send_digest(self, configuration: TelegramConfiguration, sender: DigestSender) -> int:
        if not configuration.enabled:
            raise ValueError("Telegram digest is disabled")
        return await DigestService(
            self.session,
            sender,
            profile_id=await self.profile_id(),
            min_score=configuration.min_score,
            batch_size=configuration.max_items,
            include_international=configuration.include_international,
            min_budget=configuration.min_budget,
            include_types=configuration.include_types,
        ).send_pending()

    async def profile_id(self) -> int:
        if self.settings.telegram_default_profile_id is not None:
            profile = await self.profiles.get(self.settings.telegram_default_profile_id)
        else:
            profile = await self.profiles.first()
        if profile is None:
            raise LookupError("Developer profile is not configured")
        return profile.id

    def _token_mask(self) -> str:
        if self.settings.telegram_bot_token is None:
            return "not configured"
        token = self.settings.telegram_bot_token.get_secret_value()
        return f"{token[:5]}...{token[-4:]}"

    def _next_digest(self) -> datetime | None:
        if not self.settings.scheduler_enabled:
            return None
        trigger = CronTrigger.from_crontab(
            self.settings.scheduler_cron, timezone=self.settings.scheduler_timezone
        )
        now = datetime.now(UTC)
        return trigger.get_next_fire_time(None, now)

    @staticmethod
    def _configuration(row) -> TelegramConfiguration:
        return TelegramConfiguration(
            enabled=row.enabled,
            chat_id=row.chat_id,
            min_score=row.min_score,
            min_budget=row.min_budget,
            max_items=row.max_items,
            include_international=row.include_international,
            include_types=row.include_types,
        )
