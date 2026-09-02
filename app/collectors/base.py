from abc import ABC, abstractmethod
from typing import Any

from app.schemas import CollectedItem, NormalizedOpportunity


class CollectorAdapter(ABC):
    """Contract implemented by every opportunity source."""

    source_type = "api"
    market = "unknown"
    priority = "P2"
    collection_method = "api"
    poll_interval_minutes = 60

    @property
    @abstractmethod
    def source_code(self) -> str:
        """Return a stable source identifier."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return a human-readable source name."""

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the public source base URL."""

    @abstractmethod
    async def fetch(self) -> list[CollectedItem]:
        """Fetch source-specific raw items."""

    def parse(self, raw_item: Any) -> CollectedItem:
        """Parse a fetched item; identity keeps existing adapters compatible."""
        if not isinstance(raw_item, CollectedItem):
            raise TypeError("adapter must override parse() for source-specific raw items")
        return raw_item

    @abstractmethod
    def normalize(self, item: CollectedItem) -> NormalizedOpportunity:
        """Convert one raw item to the source-independent schema."""


BaseSourceAdapter = CollectorAdapter
