"""Source collector adapters package."""

from app.collectors.b2b_center import B2BCenterCollector
from app.collectors.base import BaseSourceAdapter, CollectorAdapter
from app.collectors.fixture import FixtureCollector
from app.collectors.fl_ru import FLRuCollector
from app.collectors.freelance_ru import FreelanceRuCollector
from app.collectors.jobicy import JobicyCollector
from app.collectors.procurement import ProcurementCollectorAdapter
from app.collectors.remoteok import RemoteOKCollector
from app.collectors.weworkremotely import WeWorkRemotelyCollector
from app.collectors.workspace import WorkspaceCollector

__all__ = [
    "BaseSourceAdapter",
    "B2BCenterCollector",
    "CollectorAdapter",
    "FixtureCollector",
    "FLRuCollector",
    "FreelanceRuCollector",
    "JobicyCollector",
    "ProcurementCollectorAdapter",
    "RemoteOKCollector",
    "WeWorkRemotelyCollector",
    "WorkspaceCollector",
]
