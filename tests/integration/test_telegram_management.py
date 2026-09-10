import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.repositories import MatchRepository, UserProfileRepository
from app.schemas import MatchResult, TelegramConfiguration, UserProfileCreate
from app.services import OpportunityStorageService, PipelineService, TelegramManagementService
from app.settings import Settings

pytestmark = pytest.mark.integration


class RecordingSender:
    def __init__(self) -> None:
        self.titles: list[str] = []
        self.chat_id: int | None = None

    def set_chat_id(self, chat_id: int) -> None:
        self.chat_id = chat_id

    async def send(self, card) -> None:
        self.titles.append(card.title)


@pytest.mark.asyncio
async def test_telegram_settings_preview_and_send_share_filters() -> None:
    database_url = os.getenv("IT_RADAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("IT_RADAR_TEST_DATABASE_URL is not configured")
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection, connection.begin() as transaction:
            session = AsyncSession(bind=connection, expire_on_commit=False)
            suffix = uuid4().hex
            storage = OpportunityStorageService(session)
            source = await storage.ensure_source(
                code=f"telegram-management-{suffix}",
                name="Telegram Management",
                base_url="https://example.test",
            )
            opportunity = await storage.store_opportunity(
                source_id=source.id,
                external_id="eligible",
                title="Eligible project",
                url="https://example.test/eligible",
                market="ru",
                opportunity_type="project",
                budget_to=Decimal("200000"),
                budget_text="200 000 ₽",
                fingerprint="e" * 64,
            )
            profile = await UserProfileRepository(session).create(
                UserProfileCreate(name=f"Telegram {suffix}")
            )
            match = await MatchRepository(session).upsert(
                user_profile_id=profile.id,
                opportunity_id=opportunity.id,
                result=MatchResult(score=90, reasons=[]),
            )
            settings = Settings(
                telegram_bot_token="123456:TEST_TOKEN",
                telegram_default_profile_id=profile.id,
            )
            service = TelegramManagementService(session, settings)
            configuration = TelegramConfiguration(
                enabled=True,
                chat_id=123456789,
                min_score=80,
                min_budget=Decimal("150000"),
                max_items=5,
                include_international=False,
                include_types=["project"],
            )

            overview = await service.save(configuration)
            preview = await service.preview(configuration)
            sender = RecordingSender()
            sent = await service.send_digest(configuration, sender)

            assert overview.token_mask == "12345...OKEN"
            assert overview.configuration == configuration
            assert [card.title for card in preview] == ["Eligible project"]
            assert sent == 1
            assert sender.titles == ["Eligible project"]
            assert match.notified_at is not None

            match.notified_at = None
            await session.flush()
            scheduled_sender = RecordingSender()
            pipeline = PipelineService(
                async_sessionmaker(bind=connection, expire_on_commit=False),
                collectors={},
                ai_provider=None,
                digest_sender=scheduled_sender,
                profile_id=profile.id,
                prompt_version="telegram-management-v1",
                digest_min_score=99,
                digest_batch_size=1,
                digest_configuration_settings=settings,
            )
            report = await pipeline.run()
            assert report.notified_count == 1
            assert scheduled_sender.chat_id == 123456789

            await session.close()
            await transaction.rollback()
    finally:
        await engine.dispose()
