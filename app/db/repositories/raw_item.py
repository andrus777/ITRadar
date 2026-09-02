from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RawItem


class RawItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_or_get(
        self,
        *,
        source_id: int,
        external_id: str,
        url: str,
        payload: dict[str, Any],
        content_hash: str,
        fetched_at: datetime | None = None,
    ) -> RawItem:
        values: dict[str, Any] = {
            "source_id": source_id,
            "external_id": external_id,
            "url": url,
            "payload": payload,
            "content_hash": content_hash,
        }
        if fetched_at is not None:
            values["fetched_at"] = fetched_at

        statement = (
            insert(RawItem)
            .values(**values)
            .on_conflict_do_nothing(constraint="uq_raw_items_source_external")
            .returning(RawItem)
        )
        item = (await self.session.scalars(statement)).first()
        if item is not None:
            return item

        query = select(RawItem).where(
            RawItem.source_id == source_id,
            RawItem.external_id == external_id,
        )
        return (await self.session.scalars(query)).one()
