import hashlib
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors import CollectorAdapter
from app.db.repositories import CollectionRunRepository
from app.models import CollectionRun
from app.services.opportunity_storage import OpportunityStorageService


class CollectorService:
    """Orchestrate collection independently of source-specific formats."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.storage = OpportunityStorageService(session)
        self.runs = CollectionRunRepository(session)

    async def run(self, adapter: CollectorAdapter) -> CollectionRun:
        source = await self.storage.ensure_source(
            code=adapter.source_code,
            name=adapter.source_name,
            base_url=adapter.base_url,
        )
        run = await self.runs.start(source_id=source.id)

        try:
            items = await adapter.fetch()
        except Exception as exc:
            return await self.runs.finish(
                run,
                status="failed",
                fetched_count=0,
                new_count=0,
                error=self._error_message(exc),
            )

        errors: list[str] = []
        new_count = 0
        for item in items:
            try:
                async with self.session.begin_nested():
                    await self.storage.store_raw(
                        source_id=source.id,
                        external_id=item.external_id,
                        url=item.url,
                        payload=item.payload,
                        content_hash=self._payload_hash(item.payload),
                        fetched_at=item.fetched_at,
                    )
            except Exception as exc:
                errors.append(f"{item.external_id}: raw save: {self._error_message(exc)}")
                continue

            try:
                normalized = adapter.normalize(item)
                async with self.session.begin_nested():
                    _, created = await self.storage.store_opportunity_with_created(
                        source_id=source.id,
                        **normalized.model_dump(),
                    )
                new_count += int(created)
            except Exception as exc:
                errors.append(f"{item.external_id}: normalize/save: {self._error_message(exc)}")

        return await self.runs.finish(
            run,
            status="partial_failed" if errors else "success",
            fetched_count=len(items),
            new_count=new_count,
            error="; ".join(errors) or None,
        )

    @staticmethod
    def _payload_hash(payload: dict[str, object]) -> str:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _error_message(exc: Exception) -> str:
        message = str(exc).strip() or exc.__class__.__name__
        return message[:2000]
