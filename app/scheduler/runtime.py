from dataclasses import dataclass

from aiogram import Bot

from app.ai import OpenAICompatibleProvider
from app.bot.digest import TelegramDigestSender
from app.collectors.registry import available_collectors
from app.db.session import async_session_factory
from app.services import PipelineService
from app.settings import Settings


@dataclass(slots=True)
class PipelineRuntime:
    pipeline: PipelineService
    bot: Bot | None

    async def close(self) -> None:
        if self.bot is not None:
            await self.bot.session.close()


def build_runtime(settings: Settings) -> PipelineRuntime:
    if settings.telegram_default_profile_id is None:
        raise RuntimeError("IT_RADAR_TELEGRAM_DEFAULT_PROFILE_ID is required")

    provider = None
    if settings.ai_api_key is not None:
        provider = OpenAICompatibleProvider(
            api_key=settings.ai_api_key.get_secret_value(),
            model=settings.ai_model,
            base_url=settings.ai_base_url,
            timeout_seconds=settings.ai_timeout_seconds,
            retry_attempts=settings.http_retry_attempts,
            retry_backoff_seconds=settings.http_retry_backoff_seconds,
        )

    bot = None
    sender = None
    if settings.telegram_bot_token is not None and settings.telegram_digest_chat_id is not None:
        bot = Bot(token=settings.telegram_bot_token.get_secret_value())
        sender = TelegramDigestSender(bot, chat_id=settings.telegram_digest_chat_id)

    registrations = available_collectors(settings)
    pipeline = PipelineService(
        async_session_factory,
        collectors={code: item.adapter for code, item in registrations.items()},
        ai_provider=provider,
        digest_sender=sender,
        profile_id=settings.telegram_default_profile_id,
        prompt_version=settings.ai_prompt_version,
        digest_min_score=settings.digest_min_score,
        digest_batch_size=settings.digest_batch_size,
        include_international=settings.include_international,
        collector_enabled_defaults={
            code: item.enabled_by_default for code, item in registrations.items()
        },
    )
    return PipelineRuntime(pipeline=pipeline, bot=bot)
