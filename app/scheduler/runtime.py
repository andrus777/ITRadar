from dataclasses import dataclass

from aiogram import Bot

from app.ai import OpenAICompatibleProvider
from app.bot.digest import TelegramDigestSender
from app.collectors.registry import configured_collectors
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
        )

    bot = None
    sender = None
    if settings.telegram_bot_token is not None and settings.telegram_digest_chat_id is not None:
        bot = Bot(token=settings.telegram_bot_token.get_secret_value())
        sender = TelegramDigestSender(bot, chat_id=settings.telegram_digest_chat_id)

    pipeline = PipelineService(
        async_session_factory,
        collectors=configured_collectors(settings),
        ai_provider=provider,
        digest_sender=sender,
        profile_id=settings.telegram_default_profile_id,
        prompt_version=settings.ai_prompt_version,
        digest_min_score=settings.digest_min_score,
        digest_batch_size=settings.digest_batch_size,
    )
    return PipelineRuntime(pipeline=pipeline, bot=bot)
