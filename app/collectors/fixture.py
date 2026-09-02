import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from app.collectors.base import CollectorAdapter
from app.schemas import CollectedItem, NormalizedOpportunity


class FixtureCollector(CollectorAdapter):
    """Reference adapter that reads deterministic local JSON or HTML fixtures."""

    source_code = "fixture"
    source_name = "Fixture Source"
    base_url = "https://fixture.invalid"

    def __init__(self, *fixture_paths: Path) -> None:
        if not fixture_paths:
            raise ValueError("at least one fixture path is required")
        self.fixture_paths = fixture_paths

    async def fetch(self) -> list[CollectedItem]:
        batches = await asyncio.gather(
            *(asyncio.to_thread(self._read, path) for path in self.fixture_paths)
        )
        return [item for batch in batches for item in batch]

    def normalize(self, item: CollectedItem) -> NormalizedOpportunity:
        title = self._optional_text(item.payload.get("title"))
        if not title:
            raise ValueError(f"item {item.external_id!r} has no title")

        description = self._optional_text(item.payload.get("description"))
        published_at = self._optional_datetime(item.payload.get("published_at"))
        fingerprint_source = "\n".join((title.casefold(), description or "", item.url))

        return NormalizedOpportunity(
            external_id=item.external_id,
            title=title,
            description=description,
            url=item.url,
            budget_from=item.payload.get("budget_from"),
            budget_to=item.payload.get("budget_to"),
            currency=self._optional_text(item.payload.get("currency")),
            published_at=published_at,
            fetched_at=item.fetched_at,
            customer_name=self._optional_text(item.payload.get("customer_name")),
            location=self._optional_text(item.payload.get("location")),
            remote=item.payload.get("remote"),
            fingerprint=hashlib.sha256(fingerprint_source.encode()).hexdigest(),
        )

    def _read(self, path: Path) -> list[CollectedItem]:
        content = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            return self._read_json(content)
        if path.suffix.lower() in {".html", ".htm"}:
            return self._read_html(content)
        raise ValueError(f"unsupported fixture format: {path.suffix}")

    @staticmethod
    def _read_json(content: str) -> list[CollectedItem]:
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("JSON fixture root must be a list")
        return [CollectedItem.model_validate(entry) for entry in data]

    @staticmethod
    def _read_html(content: str) -> list[CollectedItem]:
        soup = BeautifulSoup(content, "html.parser")
        items: list[CollectedItem] = []
        for card in soup.select("article.opportunity"):
            external_id = card.get("data-id")
            url = card.get("data-url")
            if not isinstance(external_id, str) or not isinstance(url, str):
                raise ValueError("HTML opportunity requires data-id and data-url")
            payload: dict[str, Any] = {
                "title": FixtureCollector._node_text(card.select_one(".title")),
                "description": FixtureCollector._node_text(card.select_one(".description")),
                "published_at": card.get("data-published-at"),
            }
            items.append(CollectedItem(external_id=external_id, url=url, payload=payload))
        return items

    @staticmethod
    def _node_text(node: Any) -> str | None:
        return node.get_text(" ", strip=True) if node is not None else None

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _optional_datetime(value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
