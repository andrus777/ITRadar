from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Integer, cast, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models import Match, Opportunity, Source
from app.schemas.opportunity_management import OpportunityFilters


@dataclass(frozen=True, slots=True)
class OpportunityListRow:
    opportunity_id: int
    score: int | None
    title: str
    source: str
    source_code: str
    opportunity_type: str
    market: str
    category: str
    technologies: list[str]
    budget: str | None
    published_at: datetime | None
    status: str


class OpportunityManagementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(
        self,
        filters: OpportunityFilters,
        *,
        profile_id: int | None,
    ) -> tuple[list[OpportunityListRow], int]:
        score_column: ColumnElement[int | None]
        if profile_id is None:
            score_column = cast(literal(None), Integer)
            match_condition = None
        else:
            score_column = Match.score
            match_condition = (Match.opportunity_id == Opportunity.id) & (
                Match.user_profile_id == profile_id
            )

        columns = (
            Opportunity.id,
            score_column,
            Opportunity.title,
            Source.name,
            Source.code,
            Opportunity.opportunity_type,
            Opportunity.market,
            Opportunity.category,
            Opportunity.technologies,
            Opportunity.budget_text,
            Opportunity.published_at,
            Opportunity.status,
        )
        query = select(*columns).join(Source, Source.id == Opportunity.source_id)
        count_query = select(func.count(Opportunity.id)).join(
            Source, Source.id == Opportunity.source_id
        )
        if match_condition is not None:
            query = query.outerjoin(Match, match_condition)
            count_query = count_query.outerjoin(Match, match_condition)

        conditions = [Opportunity.duplicate_of_id.is_(None)]
        if filters.search.strip():
            pattern = f"%{filters.search.strip()}%"
            conditions.append(
                or_(Opportunity.title.ilike(pattern), Opportunity.description.ilike(pattern))
            )
        if filters.market != "all":
            conditions.append(Opportunity.market == filters.market)
        if filters.opportunity_type:
            conditions.append(Opportunity.opportunity_type == filters.opportunity_type)
        if filters.source:
            conditions.append(Source.code == filters.source)
        if filters.category:
            conditions.append(Opportunity.category == filters.category)
        if filters.technology:
            conditions.append(Opportunity.technologies.contains([filters.technology.casefold()]))
        if filters.budget_from is not None:
            maximum_budget = func.coalesce(Opportunity.budget_to, Opportunity.budget_from)
            conditions.append(maximum_budget >= filters.budget_from)
        if filters.budget_to is not None:
            minimum_budget = func.coalesce(Opportunity.budget_from, Opportunity.budget_to)
            conditions.append(minimum_budget <= filters.budget_to)
        if filters.score_from is not None:
            conditions.append(score_column >= filters.score_from)
        if filters.published_days is not None:
            now = datetime.now(UTC)
            if filters.published_days == 0:
                cutoff = now.astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
                cutoff = cutoff.astimezone(UTC)
            else:
                cutoff = now - timedelta(days=filters.published_days)
            conditions.append(Opportunity.published_at >= cutoff)
        if filters.status:
            conditions.append(Opportunity.status == filters.status)

        query = query.where(*conditions)
        count_query = count_query.where(*conditions)
        sort_columns: dict[str, ColumnElement[object]] = {
            "score": score_column,
            "title": Opportunity.title,
            "source": Source.name,
            "type": Opportunity.opportunity_type,
            "category": Opportunity.category,
            "budget": func.coalesce(Opportunity.budget_from, Opportunity.budget_to),
            "published": Opportunity.published_at,
            "status": Opportunity.status,
        }
        sort_column = sort_columns[filters.sort_by]
        ordering = sort_column.desc() if filters.sort_descending else sort_column.asc()
        query = query.order_by(ordering.nullslast(), Opportunity.id.desc())
        query = query.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)

        total = await self.session.scalar(count_query)
        rows = (await self.session.execute(query)).all()
        return [OpportunityListRow(*row) for row in rows], total or 0

    async def filter_values(self) -> tuple[list[tuple[str, str]], list[str]]:
        sources = (
            await self.session.execute(
                select(Source.code, Source.name)
                .join(Opportunity, Opportunity.source_id == Source.id)
                .where(Opportunity.duplicate_of_id.is_(None))
                .distinct()
                .order_by(Source.name)
            )
        ).all()
        categories = list(
            (
                await self.session.scalars(
                    select(Opportunity.category)
                    .where(Opportunity.duplicate_of_id.is_(None))
                    .distinct()
                    .order_by(Opportunity.category)
                )
            ).all()
        )
        return [(row.code, row.name) for row in sources], categories
