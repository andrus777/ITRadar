import asyncio
import hashlib
import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from app.collectors.base import CollectorAdapter
from app.http import request_with_retry
from app.schemas import CollectedItem, NormalizedOpportunity

logger = logging.getLogger(__name__)

DEFAULT_FEED_URLS = (
    "https://workspace.ru/tenders/crm/",
    "https://workspace.ru/tenders/apps-development/",
)
TENDER_ID_RE = re.compile(r"-(?P<id>\d+)/?(?:\?.*)?$")
BUDGET_RE = re.compile(
    r"(?P<budget>(?:от|до)?\s*\d[\d\s\u00a0]*(?:\s*[-–]\s*\d[\d\s\u00a0]*)?)",
    re.IGNORECASE,
)
STATUS_VALUES = ("Идет прием заявок", "Прием заявок завершен", "Завершён")
TENDER_TYPES = ("Публичный", "Приватный", "Партнерский лид")
MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}
DATE_RE = re.compile(r"(?P<day>\d{1,2})\s+(?P<month>[а-яё]+)\s+(?P<year>\d{4})", re.I)


class WorkspaceCollector(CollectorAdapter):
    """Collect public Russian digital tenders from Workspace HTML listings."""

    source_code = "workspace"
    source_name = "Workspace"
    base_url = "https://workspace.ru"
    source_type = "html"
    collection_method = "html"
    market = "ru"
    priority = "P0"
    default_opportunity_type = "tender"

    def __init__(
        self,
        *,
        count: int = 50,
        feed_urls: tuple[str, ...] = DEFAULT_FEED_URLS,
        timeout_seconds: float = 30,
        client: httpx.AsyncClient | None = None,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        if not 1 <= count <= 500:
            raise ValueError("count must be between 1 and 500")
        self.count = count
        self.feed_urls = feed_urls
        self.timeout_seconds = timeout_seconds
        self.client = client
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    async def fetch(self) -> list[CollectedItem]:
        if self.client is not None:
            batches = await self._fetch_all(self.client)
        else:
            headers = {"User-Agent": "ITRadar/0.1 (+https://github.com/andrus777/ITRadar)"}
            async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers) as client:
                batches = await self._fetch_all(client)

        unique: dict[str, CollectedItem] = {}
        for item in (item for batch in batches for item in batch):
            unique.setdefault(item.external_id, item)
        return list(unique.values())[: self.count]

    async def _fetch_all(self, client: httpx.AsyncClient) -> list[list[CollectedItem]]:
        results = await asyncio.gather(
            *(self._fetch_page(client, url) for url in self.feed_urls),
            return_exceptions=True,
        )
        batches: list[list[CollectedItem]] = []
        errors: list[Exception] = []
        for url, result in zip(self.feed_urls, results, strict=True):
            if isinstance(result, Exception):
                errors.append(result)
                logger.warning(
                    "Workspace listing failed", extra={"source": self.source_code, "url": url}
                )
            else:
                batches.append(result)
        if not batches:
            detail = "; ".join(str(error) for error in errors)
            raise RuntimeError(f"all Workspace listings failed: {detail}")
        return batches

    async def _fetch_page(self, client: httpx.AsyncClient, url: str) -> list[CollectedItem]:
        response = await request_with_retry(
            client,
            "GET",
            url,
            attempts=self.retry_attempts,
            backoff_seconds=self.retry_backoff_seconds,
        )
        return self._parse_response(response)

    def normalize(self, item: CollectedItem) -> NormalizedOpportunity:
        title = str(item.payload["title"]).strip()
        description = self._optional_text(item.payload.get("description"))
        budget_text = self._optional_text(item.payload.get("budget"))
        if budget_text and not re.search(r"₽|руб", budget_text, re.I):
            budget_text = f"{budget_text} ₽"
        fingerprint = hashlib.sha256(
            "\n".join((title.casefold(), (description or "").casefold())).encode()
        ).hexdigest()
        return NormalizedOpportunity(
            external_id=item.external_id,
            title=title,
            description=description,
            url=item.url,
            budget_text=budget_text,
            published_at=self._date(item.payload.get("published_at")),
            deadline_at=self._date(item.payload.get("deadline_at")),
            fetched_at=item.fetched_at,
            opportunity_type="tender",
            market="ru",
            fingerprint=fingerprint,
        )

    def _parse_response(self, response: httpx.Response) -> list[CollectedItem]:
        response.raise_for_status()
        if "подтвердите, что вы не робот" in response.text.casefold():
            raise RuntimeError("Workspace anti-bot verification page returned")
        soup = BeautifulSoup(response.text, "html.parser")
        items: list[CollectedItem] = []
        seen: set[str] = set()
        for link in soup.select('a[href*="/tenders/"]'):
            item = self._parse_link(link)
            if item is not None and item.external_id not in seen:
                seen.add(item.external_id)
                items.append(item)
        return items

    def _parse_link(self, link: Tag) -> CollectedItem | None:
        href = link.get("href")
        title = link.get_text(" ", strip=True)
        if not isinstance(href, str) or not title:
            return None
        match = TENDER_ID_RE.search(href)
        if not match:
            return None
        card = self._card_container(link)
        if card is None:
            return None
        text = card.get_text(" ", strip=True)
        published = self._labeled_date(text, "Опубликован")
        deadline = self._labeled_date(text, "Крайний срок приема заявок")
        if published is None or deadline is None:
            return None
        budget = self._budget(text, title)
        payload: dict[str, Any] = {
            "title": title,
            "description": self._description(card, title),
            "budget": budget,
            "published_at": published,
            "deadline_at": deadline,
            "status": next((value for value in STATUS_VALUES if value in text), None),
            "tender_type": next((value for value in TENDER_TYPES if value in text), None),
        }
        return CollectedItem(
            external_id=match.group("id"),
            url=urljoin(self.base_url, href),
            payload=payload,
        )

    @staticmethod
    def _card_container(link: Tag) -> Tag | None:
        current = link.parent
        for _ in range(8):
            if not isinstance(current, Tag):
                return None
            text = current.get_text(" ", strip=True)
            tender_links = current.find_all("a", href=TENDER_ID_RE)
            if (
                "Опубликован" in text
                and "Крайний срок приема заявок" in text
                and len(tender_links) == 1
            ):
                return current
            current = current.parent
        return None

    @staticmethod
    def _labeled_date(text: str, label: str) -> str | None:
        remainder = text.partition(label)[2]
        match = DATE_RE.search(remainder)
        return match.group(0) if match else None

    @staticmethod
    def _budget(text: str, title: str) -> str | None:
        prefix = text.partition(title)[0]
        suffix = text.partition(title)[2].partition("Опубликован")[0]
        match = BUDGET_RE.search(suffix) or BUDGET_RE.search(prefix)
        return re.sub(r"\s+", " ", match.group("budget")).strip() if match else None

    @staticmethod
    def _description(card: Tag, title: str) -> str | None:
        node = card.select_one("[data-description], .tender-description, .description")
        if node is None:
            return None
        value = node.get_text(" ", strip=True)
        return value if value and value != title else None

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    @staticmethod
    def _date(value: Any) -> datetime | None:
        if not value:
            return None
        match = DATE_RE.search(str(value))
        if not match:
            raise ValueError(f"invalid Workspace date: {value!r}")
        month = MONTHS.get(match.group("month").casefold())
        if month is None:
            raise ValueError(f"invalid Workspace month: {match.group('month')!r}")
        return datetime(int(match.group("year")), month, int(match.group("day")), tzinfo=UTC)
