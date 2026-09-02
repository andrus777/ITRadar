from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import PipelineRepository
from app.schemas import OpportunityCard
from app.services.opportunity_browser import OpportunityBrowserService


class DigestSender(Protocol):
    def send(self, card: OpportunityCard) -> Awaitable[None]: ...


class DigestService:
    def __init__(
        self,
        session: AsyncSession,
        sender: DigestSender,
        *,
        profile_id: int,
        min_score: int,
        batch_size: int = 20,
    ) -> None:
        self.repository = PipelineRepository(session)
        self.sender = sender
        self.profile_id = profile_id
        self.min_score = min_score
        self.batch_size = batch_size

    async def send_pending(self) -> int:
        pending = await self.repository.pending_digest(
            profile_id=self.profile_id,
            min_score=self.min_score,
            limit=self.batch_size,
        )
        sent = 0
        for item in pending:
            card = OpportunityBrowserService.card_from_row(item.card)
            await self.sender.send(card)
            item.match.notified_at = datetime.now(UTC)
            sent += 1
        return sent
