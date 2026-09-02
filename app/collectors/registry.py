from collections.abc import Callable

from app.collectors.base import CollectorAdapter
from app.collectors.jobicy import JobicyCollector
from app.collectors.remoteok import RemoteOKCollector
from app.collectors.weworkremotely import WeWorkRemotelyCollector
from app.settings import Settings

CollectorFactory = Callable[[], CollectorAdapter]


def configured_collectors(settings: Settings) -> dict[str, CollectorAdapter]:
    """Build enabled collectors solely from environment-backed settings."""
    factories: dict[str, tuple[bool, CollectorFactory]] = {
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
    }
    return {name: factory() for name, (enabled, factory) in factories.items() if enabled}
