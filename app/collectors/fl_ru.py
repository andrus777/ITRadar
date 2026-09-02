import asyncio
import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.collectors.base import CollectorAdapter
from app.http import request_with_retry
from app.schemas import CollectedItem, NormalizedOpportunity

DEFAULT_CATEGORIES = (
    "программирование",
    "python",
    "интеграция по api",
    "разработка чат-ботов",
    "машинное обучение",
    "парсинг данных",
    "1с-программирование",
    "разработка crm и erp",
    "devops",
    "fullstack",
    "веб-программирование",
    "mobile",
    "создание mvp",
    "n8n",
    "ai — искусственный интеллект",
    "автоматизация бизнеса",
)
PROJECT_ID_RE = re.compile(r"/projects/(?P<id>\d+)/")
BUDGET_RE = re.compile(r"\s*\(Бюджет:\s*(?P<budget>[^)]+)\)\s*$", re.IGNORECASE)


class FLRuCollector(CollectorAdapter):
    """Collect Russian IT projects from FL.ru's official public RSS feed."""

    source_code = "fl_ru"
    source_name = "FL.ru"
    base_url = "https://www.fl.ru"
    source_type = "rss"
    collection_method = "rss"
    market = "ru"
    priority = "P0"
    default_opportunity_type = "freelance"
    endpoint = "https://www.fl.ru/rss/all.xml"

    def __init__(
        self,
        *,
        count: int = 50,
        categories: tuple[str, ...] = DEFAULT_CATEGORIES,
        feed_urls: tuple[str, ...] | None = None,
        timeout_seconds: float = 30,
        client: httpx.AsyncClient | None = None,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        if not 1 <= count <= 500:
            raise ValueError("count must be between 1 and 500")
        self.count = count
        self.categories = tuple(value.casefold().strip() for value in categories if value.strip())
        self.feed_urls = feed_urls or (self.endpoint,)
        self.timeout_seconds = timeout_seconds
        self.client = client
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    async def fetch(self) -> list[CollectedItem]:
        if self.client is not None:
            batches = await asyncio.gather(
                *(self._fetch_feed(self.client, url) for url in self.feed_urls)
            )
        else:
            headers = {
                "Accept": "application/rss+xml, application/xml",
                "User-Agent": "ITRadar/0.1 (+https://github.com/andrus777/ITRadar)",
            }
            async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers) as client:
                batches = await asyncio.gather(
                    *(self._fetch_feed(client, url) for url in self.feed_urls)
                )

        unique: dict[str, CollectedItem] = {}
        for item in (item for batch in batches for item in batch):
            unique.setdefault(item.external_id, item)
        return list(unique.values())[: self.count]

    async def _fetch_feed(self, client: httpx.AsyncClient, url: str) -> list[CollectedItem]:
        response = await request_with_retry(
            client,
            "GET",
            url,
            attempts=self.retry_attempts,
            backoff_seconds=self.retry_backoff_seconds,
        )
        return self._parse_response(response)

    def normalize(self, item: CollectedItem) -> NormalizedOpportunity:
        raw_title = self._text(item.payload.get("title"))
        if not raw_title:
            raise ValueError(f"FL.ru item {item.external_id!r} has no title")
        budget_match = BUDGET_RE.search(raw_title)
        budget_text = budget_match.group("budget").strip() if budget_match else None
        title = raw_title[: budget_match.start()].strip() if budget_match else raw_title
        description = self._text(item.payload.get("description"))
        fingerprint = hashlib.sha256(
            "\n".join((title.casefold(), (description or "").casefold())).encode()
        ).hexdigest()
        return NormalizedOpportunity(
            external_id=item.external_id,
            title=title,
            description=description,
            url=item.url,
            budget_text=budget_text,
            published_at=self._datetime(item.payload.get("pubDate")),
            fetched_at=item.fetched_at,
            opportunity_type="freelance",
            market="ru",
            fingerprint=fingerprint,
        )

    def _parse_response(self, response: httpx.Response) -> list[CollectedItem]:
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items: list[CollectedItem] = []
        for node in root.findall("./channel/item"):
            category = self._text(node.findtext("category"))
            if not self._is_target_category(category):
                continue
            url = self._text(node.findtext("link"))
            guid = self._text(node.findtext("guid")) or url
            title = self._text(node.findtext("title"))
            if not url or not guid or not title:
                continue
            match = PROJECT_ID_RE.search(url)
            external_id = match.group("id") if match else hashlib.sha256(guid.encode()).hexdigest()
            payload: dict[str, Any] = {
                "title": title,
                "description": node.findtext("description"),
                "category": category,
                "pubDate": node.findtext("pubDate"),
                "guid": guid,
            }
            items.append(CollectedItem(external_id=external_id, url=url, payload=payload))
        return items

    def _is_target_category(self, category: str | None) -> bool:
        if not category:
            return False
        normalized = category.casefold()
        return any(term in normalized for term in self.categories)

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _datetime(value: Any) -> datetime | None:
        return parsedate_to_datetime(str(value)) if value else None
