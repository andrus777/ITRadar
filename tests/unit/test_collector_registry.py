from app.collectors.registry import configured_collectors
from app.settings import Settings


def test_disabled_source_is_removed_by_configuration() -> None:
    settings = Settings(
        jobicy_enabled=True,
        remoteok_enabled=False,
        weworkremotely_enabled=True,
        jobicy_timeout_seconds=11,
        weworkremotely_timeout_seconds=17,
    )

    collectors = configured_collectors(settings)

    assert set(collectors) == {"jobicy", "weworkremotely"}
    assert collectors["jobicy"].timeout_seconds == 11
    assert collectors["weworkremotely"].timeout_seconds == 17
