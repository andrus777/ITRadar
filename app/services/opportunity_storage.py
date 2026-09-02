from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import OpportunityRepository, RawItemRepository, SourceRepository
from app.models import Opportunity, RawItem, Source


class OpportunityStorageService:
    """Persist collected source data without exposing SQL to collectors."""

    def __init__(self, session: AsyncSession) -> None:
        self.sources = SourceRepository(session)
        self.raw_items = RawItemRepository(session)
        self.opportunities = OpportunityRepository(session)

    async def ensure_source(
        self, *, code: str, name: str, base_url: str, **metadata: Any
    ) -> Source:
        source = await self.sources.get_by_code(code)
        if source is not None:
            return await self.sources.update_metadata(
                source, name=name, base_url=base_url, **metadata
            )
        return await self.sources.create(code=code, name=name, base_url=base_url, **metadata)

    async def store_raw(
        self,
        *,
        source_id: int,
        external_id: str,
        url: str,
        payload: dict[str, Any],
        content_hash: str,
        fetched_at: datetime | None = None,
    ) -> RawItem:
        return await self.raw_items.add_or_get(
            source_id=source_id,
            external_id=external_id,
            url=url,
            payload=payload,
            content_hash=content_hash,
            fetched_at=fetched_at,
        )

    async def store_opportunity(self, **values: Any) -> Opportunity:
        return await self.opportunities.add_or_get(**values)

    async def store_opportunity_with_created(self, **values: Any) -> tuple[Opportunity, bool]:
        return await self.opportunities.add_or_get_with_created(**values)
