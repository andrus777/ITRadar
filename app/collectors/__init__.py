"""Source collector adapters package."""

from app.collectors.base import CollectorAdapter
from app.collectors.fixture import FixtureCollector

__all__ = ["CollectorAdapter", "FixtureCollector"]
