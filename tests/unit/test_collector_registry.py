from app.collectors import JobicyCollector, RemoteOKCollector, WeWorkRemotelyCollector
from app.collectors.registry import available_collectors, configured_collectors
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

    assert set(collectors) == {
        "b2b_center",
        "fl_ru",
        "freelance_ru",
        "jobicy",
        "telegram_freevacanciesit",
        "telegram_job_for_bots",
        "weworkremotely",
        "workspace",
    }
    assert collectors["fl_ru"].market == "ru"
    assert collectors["jobicy"].timeout_seconds == 11
    assert collectors["weworkremotely"].timeout_seconds == 17
    assert collectors["workspace"].market == "ru"
    assert collectors["freelance_ru"].default_opportunity_type == "freelance"
    assert collectors["b2b_center"].source_type == "procurement"
    assert collectors["telegram_job_for_bots"].source_type == "telegram"


def test_existing_job_sources_are_secondary_international_vacancies() -> None:
    for collector_type in (JobicyCollector, RemoteOKCollector, WeWorkRemotelyCollector):
        assert collector_type.market == "international"
        assert collector_type.priority == "P2"
        assert collector_type.default_opportunity_type == "vacancy"


def test_international_digest_is_disabled_by_default() -> None:
    assert Settings().include_international is False


def test_available_collectors_retains_disabled_sources_for_desktop_management() -> None:
    collectors = available_collectors(Settings(remoteok_enabled=False))

    assert collectors["remoteok"].enabled_by_default is False
    assert isinstance(collectors["remoteok"].adapter, RemoteOKCollector)
