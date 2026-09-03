import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from app.collectors.base import CollectorAdapter
from app.http import request_with_retry
from app.schemas import CollectedItem, NormalizedOpportunity

DEFAULT_FEED_URL = "https://freelance.ru/task"
DEFAULT_CATEGORIES = ("Веб-разработка и IT", "Искусственный интеллект")
TASK_ID_RE = re.compile(r"^/task/view/(?P<id>\d+)/?(?:\?.*)?$")
RELATIVE_TIME_RE = re.compile(
    r"(?P<count>\d+)\s+(?P<unit>минут(?:у|ы)?|час(?:а|ов)?|д(?:ень|ня|ней))\s+назад",
    re.IGNORECASE,
)


class FreelanceRuCollector(CollectorAdapter):
    """Collect public Web/IT and AI tasks from Freelance.ru."""

    source_code = "freelance_ru"
    source_name = "Freelance.ru"
    base_url = "https://freelance.ru"
    source_type = "html"
    collection_method = "html"
    market = "ru"
    priority = "P0"
    default_opportunity_type = "freelance"

    def __init__(
        self,
        *,
        count: int = 50,
        feed_url: str = DEFAULT_FEED_URL,
        categories: tuple[str, ...] = DEFAULT_CATEGORIES,
        timeout_seconds: float = 30,
        client: httpx.AsyncClient | None = None,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        if not 1 <= count <= 500:
            raise ValueError("count must be between 1 and 500")
        self.count = count
        self.feed_url = feed_url
        self.categories = frozenset(category.casefold() for category in categories)
        self.timeout_seconds = timeout_seconds
        self.client = client
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    async def fetch(self) -> list[CollectedItem]:
        if self.client is not None:
            return await self._fetch(self.client)
        headers = {"User-Agent": "ITRadar/0.1 (+https://github.com/andrus777/ITRadar)"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers) as client:
            return await self._fetch(client)

    async def _fetch(self, client: httpx.AsyncClient) -> list[CollectedItem]:
        response = await request_with_retry(
            client,
            "GET",
            self.feed_url,
            attempts=self.retry_attempts,
            backoff_seconds=self.retry_backoff_seconds,
        )
        return self._parse_response(response)[: self.count]

    def normalize(self, item: CollectedItem) -> NormalizedOpportunity:
        title = str(item.payload["title"]).strip()
        description = self._optional_text(item.payload.get("description"))
        fingerprint = hashlib.sha256(
            "\n".join((title.casefold(), (description or "").casefold())).encode()
        ).hexdigest()
        return NormalizedOpportunity(
            external_id=item.external_id,
            title=title,
            description=description,
            source_category=str(item.payload["category"]),
            url=item.url,
            budget_text=self._optional_text(item.payload.get("budget")),
            published_at=self._published_at(item.payload.get("published_at"), item.fetched_at),
            fetched_at=item.fetched_at,
            opportunity_type="freelance",
            market="ru",
            fingerprint=fingerprint,
        )

    def _parse_response(self, response: httpx.Response) -> list[CollectedItem]:
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        items: list[CollectedItem] = []
        seen: set[str] = set()
        for card in soup.select("article.task-card"):
            item = self._parse_card(card)
            if item is not None and item.external_id not in seen:
                seen.add(item.external_id)
                items.append(item)
        return items

    def _parse_card(self, card: Tag) -> CollectedItem | None:
        link = card.select_one("a.task-card__title-link")
        category_node = card.select_one(".task-chip--cat")
        if link is None or category_node is None:
            return None
        href = link.get("href")
        title = link.get_text(" ", strip=True)
        category = category_node.get_text(" ", strip=True)
        if not isinstance(href, str) or not title or category.casefold() not in self.categories:
            return None
        match = TASK_ID_RE.match(href)
        if match is None:
            return None
        description_node = card.select_one(".task-card__desc")
        budget_node = card.select_one(".task-card__budget")
        time_node = card.select_one(".task-card__foot-item")
        payload: dict[str, Any] = {
            "title": title,
            "description": description_node.get_text(" ", strip=True) if description_node else None,
            "budget": budget_node.get_text(" ", strip=True) if budget_node else None,
            "category": category,
            "published_at": time_node.get_text(" ", strip=True) if time_node else None,
        }
        return CollectedItem(
            external_id=match.group("id"),
            url=urljoin(self.base_url, href),
            payload=payload,
        )

    @staticmethod
    def _published_at(value: Any, fetched_at: datetime) -> datetime | None:
        if value is None:
            return None
        text = str(value).strip().casefold()
        if text in {"только что", "сейчас"}:
            return fetched_at.astimezone(UTC)
        match = RELATIVE_TIME_RE.search(text)
        if match is None:
            return None
        count = int(match.group("count"))
        unit = match.group("unit")
        if unit.startswith("минут"):
            delta = timedelta(minutes=count)
        elif unit.startswith("час"):
            delta = timedelta(hours=count)
        else:
            delta = timedelta(days=count)
        return fetched_at.astimezone(UTC) - delta

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None
