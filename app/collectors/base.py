from abc import ABC, abstractmethod

from app.schemas import CollectedItem, NormalizedOpportunity


class CollectorAdapter(ABC):
    """Contract implemented by every opportunity source."""

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

    @abstractmethod
    def normalize(self, item: CollectedItem) -> NormalizedOpportunity:
        """Convert one raw item to the source-independent schema."""
