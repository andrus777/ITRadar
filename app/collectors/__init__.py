"""Source collector adapters package."""

from app.collectors.base import BaseSourceAdapter, CollectorAdapter
from app.collectors.fixture import FixtureCollector
from app.collectors.fl_ru import FLRuCollector
from app.collectors.jobicy import JobicyCollector
from app.collectors.remoteok import RemoteOKCollector
from app.collectors.weworkremotely import WeWorkRemotelyCollector

__all__ = [
    "BaseSourceAdapter",
    "CollectorAdapter",
    "FixtureCollector",
    "FLRuCollector",
    "JobicyCollector",
    "RemoteOKCollector",
    "WeWorkRemotelyCollector",
]
