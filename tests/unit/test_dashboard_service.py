from decimal import Decimal

from app.db.repositories.dashboard import DashboardStats
from app.services.dashboard import DashboardService


def test_dashboard_metrics_and_system_statuses_are_deterministic() -> None:
    statistics = DashboardStats(
        new_count=12,
        matched_count=4,
        healthy_sources=5,
        total_sources=7,
        degraded_sources=1,
        unhealthy_sources=1,
        error_count=2,
        average_budget=Decimal("187500"),
        ai_queue_count=8,
    )

    metrics = DashboardService._metrics(statistics)
    statuses = DashboardService._statuses(
        statistics,
        ai_enabled=True,
        telegram_enabled=False,
    )

    assert {metric.key: metric.value for metric in metrics} == {
        "new": "12",
        "matched": "4",
        "sources": "5/7",
        "errors": "2",
        "budget": "188k",
        "ai_queue": "8",
    }
    assert {status.key: status.state for status in statuses} == {
        "database": "ok",
        "collectors": "failure",
        "ai": "ok",
        "telegram": "disabled",
    }
