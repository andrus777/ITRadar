from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Opportunity
from app.schemas import NormalizedOpportunity


class DeduplicationService:
    """Find a canonical cross-source opportunity using conservative rules."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_duplicate(
        self, *, source_id: int, opportunity: NormalizedOpportunity
    ) -> Opportunity | None:
        base_filters = (
            Opportunity.source_id != source_id,
            Opportunity.duplicate_of_id.is_(None),
        )
        if opportunity.normalized_url:
            by_url = await self.session.scalar(
                select(Opportunity)
                .where(
                    *base_filters,
                    Opportunity.normalized_url == opportunity.normalized_url,
                )
                .order_by(Opportunity.id)
                .limit(1)
            )
            if by_url is not None:
                return by_url

        by_fingerprint = await self.session.scalar(
            select(Opportunity)
            .where(*base_filters, Opportunity.fingerprint == opportunity.fingerprint)
            .order_by(Opportunity.id)
            .limit(1)
        )
        if by_fingerprint is not None:
            return by_fingerprint

        if not opportunity.normalized_title or not opportunity.description:
            return None
        candidates = (
            await self.session.scalars(
                select(Opportunity)
                .where(*base_filters, Opportunity.description.is_not(None))
                .order_by(Opportunity.id.desc())
                .limit(200)
            )
        ).all()
        for candidate in candidates:
            if not candidate.normalized_title or not candidate.description:
                continue
            title_score = SequenceMatcher(
                None, opportunity.normalized_title, candidate.normalized_title
            ).ratio()
            description_score = SequenceMatcher(
                None, opportunity.description.casefold(), candidate.description.casefold()
            ).ratio()
            if title_score >= 0.96 and description_score >= 0.90:
                return candidate
        return None
