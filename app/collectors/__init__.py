"""Source collector adapters package."""

from app.collectors.base import CollectorAdapter
from app.collectors.fixture import FixtureCollector
from app.collectors.jobicy import JobicyCollector
from app.collectors.remoteok import RemoteOKCollector
from app.collectors.weworkremotely import WeWorkRemotelyCollector

__all__ = [
    "CollectorAdapter",
    "FixtureCollector",
    "JobicyCollector",
    "RemoteOKCollector",
    "WeWorkRemotelyCollector",
]
