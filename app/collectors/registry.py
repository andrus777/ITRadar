from collections.abc import Callable
from dataclasses import dataclass

from app.collectors.b2b_center import B2BCenterCollector
from app.collectors.base import CollectorAdapter
from app.collectors.fl_ru import FLRuCollector
from app.collectors.freelance_ru import FreelanceRuCollector
from app.collectors.jobicy import JobicyCollector
from app.collectors.remoteok import RemoteOKCollector
from app.collectors.telegram import TelegramChannelCollector, parse_telegram_whitelist
from app.collectors.weworkremotely import WeWorkRemotelyCollector
from app.collectors.workspace import WorkspaceCollector
from app.settings import Settings

CollectorFactory = Callable[[], CollectorAdapter]


@dataclass(frozen=True, slots=True)
class CollectorRegistration:
    enabled_by_default: bool
    adapter: CollectorAdapter


def available_collectors(settings: Settings) -> dict[str, CollectorRegistration]:
    """Build every known collector and retain its initial configuration state."""
    factories: dict[str, tuple[bool, CollectorFactory]] = {
        "b2b_center": (
            settings.b2b_center_enabled,
            lambda: B2BCenterCollector(
                timeout_seconds=settings.b2b_center_timeout_seconds,
                retry_attempts=settings.http_retry_attempts,
                retry_backoff_seconds=settings.http_retry_backoff_seconds,
            ),
        ),
        "freelance_ru": (
            settings.freelance_ru_enabled,
            lambda: FreelanceRuCollector(
                categories=tuple(
                    value.strip()
                    for value in settings.freelance_ru_categories.split(",")
                    if value.strip()
                ),
                timeout_seconds=settings.freelance_ru_timeout_seconds,
                retry_attempts=settings.http_retry_attempts,
                retry_backoff_seconds=settings.http_retry_backoff_seconds,
            ),
        ),
        "fl_ru": (
            settings.fl_ru_enabled,
            lambda: FLRuCollector(
                categories=tuple(
                    value.strip() for value in settings.fl_ru_categories.split(",") if value.strip()
                ),
                timeout_seconds=settings.fl_ru_timeout_seconds,
                retry_attempts=settings.http_retry_attempts,
                retry_backoff_seconds=settings.http_retry_backoff_seconds,
            ),
        ),
        "jobicy": (
            settings.jobicy_enabled,
            lambda: JobicyCollector(
                timeout_seconds=settings.jobicy_timeout_seconds,
                retry_attempts=settings.http_retry_attempts,
                retry_backoff_seconds=settings.http_retry_backoff_seconds,
            ),
        ),
        "remoteok": (
            settings.remoteok_enabled,
            lambda: RemoteOKCollector(
                timeout_seconds=settings.remoteok_timeout_seconds,
                retry_attempts=settings.http_retry_attempts,
                retry_backoff_seconds=settings.http_retry_backoff_seconds,
            ),
        ),
        "weworkremotely": (
            settings.weworkremotely_enabled,
            lambda: WeWorkRemotelyCollector(
                timeout_seconds=settings.weworkremotely_timeout_seconds,
                retry_attempts=settings.http_retry_attempts,
                retry_backoff_seconds=settings.http_retry_backoff_seconds,
            ),
        ),
        "workspace": (
            settings.workspace_enabled,
            lambda: WorkspaceCollector(
                timeout_seconds=settings.workspace_timeout_seconds,
                retry_attempts=settings.http_retry_attempts,
                retry_backoff_seconds=settings.http_retry_backoff_seconds,
            ),
        ),
    }
    collectors = {
        name: CollectorRegistration(enabled_by_default=enabled, adapter=factory())
        for name, (enabled, factory) in factories.items()
    }
    for channel in parse_telegram_whitelist(settings.telegram_source_whitelist):
        collector = TelegramChannelCollector(
            channel=channel,
            timeout_seconds=settings.telegram_source_timeout_seconds,
            retry_attempts=settings.http_retry_attempts,
            retry_backoff_seconds=settings.http_retry_backoff_seconds,
        )
        collectors[collector.source_code] = CollectorRegistration(
            enabled_by_default=channel.enabled,
            adapter=collector,
        )
    return collectors


def configured_collectors(settings: Settings) -> dict[str, CollectorAdapter]:
    """Build collectors enabled by bootstrap environment configuration."""
    return {
        code: registration.adapter
        for code, registration in available_collectors(settings).items()
        if registration.enabled_by_default
    }
