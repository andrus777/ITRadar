from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.dashboard import DashboardRepository, DashboardStats
from app.schemas.dashboard import (
    DashboardMetric,
    DashboardOpportunity,
    DashboardSnapshot,
    DashboardSystemStatus,
)


class DashboardService:
    """Build a database-independent snapshot for administrative clients."""

    def __init__(self, session: AsyncSession) -> None:
        self.repository = DashboardRepository(session)

    async def snapshot(
        self,
        *,
        profile_id: int | None,
        ai_enabled: bool,
        telegram_enabled: bool,
    ) -> DashboardSnapshot:
        statistics = await self.repository.statistics(profile_id=profile_id)
        rows = await self.repository.top_opportunities(profile_id=profile_id)
        return DashboardSnapshot(
            metrics=self._metrics(statistics),
            opportunities=[
                DashboardOpportunity(
                    opportunity_id=row.opportunity_id,
                    score=row.score,
                    title=row.title,
                    source=row.source,
                    budget=row.budget,
                    opportunity_type=row.opportunity_type,
                    published_at=row.published_at,
                )
                for row in rows
            ],
            statuses=self._statuses(
                statistics,
                ai_enabled=ai_enabled,
                telegram_enabled=telegram_enabled,
            ),
            loaded_at=datetime.now(UTC),
        )

    @classmethod
    def _metrics(cls, statistics: DashboardStats) -> list[DashboardMetric]:
        return [
            DashboardMetric(key="new", label="Новые за 24 часа", value=str(statistics.new_count)),
            DashboardMetric(
                key="matched",
                label="Подходят мне",
                value=str(statistics.matched_count),
                detail="score ≥ 80",
            ),
            DashboardMetric(
                key="sources",
                label="Источники OK",
                value=f"{statistics.healthy_sources}/{statistics.total_sources}",
            ),
            DashboardMetric(
                key="errors",
                label="Ошибки",
                value=str(statistics.error_count),
                detail="за 24 часа",
            ),
            DashboardMetric(
                key="budget",
                label="Средний бюджет",
                value=cls._format_budget(statistics.average_budget),
            ),
            DashboardMetric(key="ai_queue", label="AI Queue", value=str(statistics.ai_queue_count)),
        ]

    @staticmethod
    def _statuses(
        statistics: DashboardStats,
        *,
        ai_enabled: bool,
        telegram_enabled: bool,
    ) -> list[DashboardSystemStatus]:
        if statistics.total_sources == 0:
            collector_state, collector_detail = "disabled", "нет включённых источников"
        elif statistics.unhealthy_sources:
            collector_state, collector_detail = "failure", "есть недоступные источники"
        elif statistics.degraded_sources:
            collector_state, collector_detail = "warning", "есть предупреждения"
        else:
            collector_state, collector_detail = "ok", "источники работают"
        return [
            DashboardSystemStatus(key="database", label="Database", state="ok", detail="connected"),
            DashboardSystemStatus(
                key="collectors", label="Collectors", state=collector_state, detail=collector_detail
            ),
            DashboardSystemStatus(
                key="ai",
                label="AI",
                state="ok" if ai_enabled else "disabled",
                detail="configured" if ai_enabled else "API key не задан",
            ),
            DashboardSystemStatus(
                key="telegram",
                label="Telegram",
                state="ok" if telegram_enabled else "disabled",
                detail="configured" if telegram_enabled else "token не задан",
            ),
        ]

    @staticmethod
    def _format_budget(value: Decimal | None) -> str:
        if value is None:
            return "—"
        amount = int(value)
        if amount >= 1_000_000:
            return f"{amount / 1_000_000:.1f}M"
        if amount >= 1_000:
            return f"{amount / 1_000:.0f}k"
        return str(amount)
