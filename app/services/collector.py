import hashlib
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors import CollectorAdapter
from app.db.repositories import CollectionRunRepository
from app.models import CollectionRun
from app.services.deduplication import DeduplicationService
from app.services.normalization import OpportunityNormalizationService
from app.services.opportunity_storage import OpportunityStorageService

logger = logging.getLogger(__name__)


class CollectorService:
    """Orchestrate collection independently of source-specific formats."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.storage = OpportunityStorageService(session)
        self.runs = CollectionRunRepository(session)
        self.normalizer = OpportunityNormalizationService()
        self.deduplication = DeduplicationService(session)

    async def run(self, adapter: CollectorAdapter) -> CollectionRun:
        source = await self.storage.ensure_source(
            code=adapter.source_code,
            name=adapter.source_name,
            base_url=adapter.base_url,
            source_type=adapter.source_type,
            market=adapter.market,
            priority=adapter.priority,
            collection_method=adapter.collection_method,
            poll_interval_minutes=adapter.poll_interval_minutes,
        )
        run = await self.runs.start(source_id=source.id)
        context = {"run_id": run.id, "source": adapter.source_code}
        logger.info("collection run started", extra=context)

        try:
            items = await adapter.fetch()
        except Exception as exc:
            error = self._error_message(exc)
            logger.error("collection fetch failed", extra={**context, "error": error})
            result = await self.runs.finish(
                run,
                status="failed",
                fetched_count=0,
                new_count=0,
                error=error,
            )
            await self.storage.sources.record_run_result(source, status="failed", error=error)
            return result

        errors: list[str] = []
        new_count = 0
        duplicate_count = 0
        for raw_item in items:
            try:
                item = adapter.parse(raw_item)
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
                item_id = getattr(raw_item, "external_id", "unknown")
                error = f"{item_id}: parse/raw save: {self._error_message(exc)}"
                errors.append(error)
                logger.warning("collection item failed", extra={**context, "error": error})
                continue

            try:
                normalized = adapter.normalize(item)
                defaults: dict[str, str] = {}
                if normalized.market == "unknown":
                    defaults["market"] = adapter.market
                if normalized.opportunity_type == "unknown":
                    defaults["opportunity_type"] = adapter.default_opportunity_type
                normalized = self.normalizer.normalize(normalized.model_copy(update=defaults))
                async with self.session.begin_nested():
                    duplicate = await self.deduplication.find_duplicate(
                        source_id=source.id,
                        opportunity=normalized,
                    )
                    _, created = await self.storage.store_opportunity_with_created(
                        source_id=source.id,
                        duplicate_of_id=duplicate.id if duplicate else None,
                        **normalized.model_dump(),
                    )
                if created and duplicate is not None:
                    duplicate_count += 1
                elif created:
                    new_count += 1
            except Exception as exc:
                error = f"{item.external_id}: normalize/save: {self._error_message(exc)}"
                errors.append(error)
                logger.warning("collection item failed", extra={**context, "error": error})

        result = await self.runs.finish(
            run,
            status="partial_failed" if errors else "success",
            fetched_count=len(items),
            new_count=new_count,
            duplicate_count=duplicate_count,
            rejected_count=len(errors),
            error="; ".join(errors) or None,
        )
        await self.storage.sources.record_run_result(
            source,
            status=result.status,
            error=result.error,
        )
        logger.info(
            "collection run finished",
            extra={
                **context,
                "status": result.status,
                "fetched_count": result.fetched_count,
                "new_count": result.new_count,
                "duplicate_count": result.duplicate_count,
                "rejected_count": result.rejected_count,
                "error": result.error,
            },
        )
        return result

    @staticmethod
    def _payload_hash(payload: dict[str, object]) -> str:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _error_message(exc: Exception) -> str:
        message = str(exc).strip() or exc.__class__.__name__
        return message[:2000]
