"""Source collector adapters package."""

from app.collectors.base import CollectorAdapter
from app.collectors.fixture import FixtureCollector
from app.collectors.jobicy import JobicyCollector

__all__ = ["CollectorAdapter", "FixtureCollector", "JobicyCollector"]
