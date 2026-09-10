import asyncio
import hashlib
import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup, Tag

from app.collectors.procurement import ProcurementCollectorAdapter
from app.http import request_with_retry
from app.schemas import CollectedItem, NormalizedOpportunity

logger = logging.getLogger(__name__)

SEARCH_URL = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"
MOSCOW_TZ = ZoneInfo("Europe/Moscow")
NUMBER_RE = re.compile(r"(?:№\s*)?(?P<number>\d{10,})")
DATE_RE = re.compile(r"(?P<date>\d{2}\.\d{2}\.\d{4})(?:\s+(?P<time>\d{2}:\d{2}))?")
DEFAULT_QUERIES = (
    "разработка программного обеспечения",
    "информационная система",
    "сопровождение программного обеспечения",
)


class Zakupki44FZCollector(ProcurementCollectorAdapter):
    """Collect IT notices from the public 44-FZ search showcase of EIS."""

    source_code = "zakupki_44fz"
    source_name = "ЕИС Закупки — 44-ФЗ"
    base_url = "https://zakupki.gov.ru"
    priority = "P0"

    def __init__(
        self,
        *,
        queries: tuple[str, ...] = DEFAULT_QUERIES,
        count: int = 100,
        search_url: str = SEARCH_URL,
        timeout_seconds: float = 30,
        client: httpx.AsyncClient | None = None,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        if not queries:
            raise ValueError("at least one 44-FZ search query is required")
        if not 1 <= count <= 500:
            raise ValueError("count must be between 1 and 500")
        self.queries = queries
        self.count = count
        self.search_url = search_url
        self.timeout_seconds = timeout_seconds
        self.client = client
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    async def fetch(self) -> list[CollectedItem]:
        if self.client is not None:
            batches = await self._fetch_all(self.client)
        else:
            headers = {
                "User-Agent": "ITRadar/0.1 (+https://github.com/andrus777/ITRadar)",
                "Accept-Language": "ru-RU,ru;q=0.9",
            }
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, headers=headers, follow_redirects=True
            ) as client:
                batches = await self._fetch_all(client)
        unique: dict[str, CollectedItem] = {}
        for item in (item for batch in batches for item in batch):
            unique.setdefault(item.external_id, item)
        return list(unique.values())[: self.count]

    async def _fetch_all(self, client: httpx.AsyncClient) -> list[list[CollectedItem]]:
        results = await asyncio.gather(
            *(self._fetch_query(client, query) for query in self.queries), return_exceptions=True
        )
        batches: list[list[CollectedItem]] = []
        errors: list[Exception] = []
        for query, result in zip(self.queries, results, strict=True):
            if isinstance(result, Exception):
                errors.append(result)
                logger.warning(
                    "EIS 44-FZ query failed",
                    extra={"source": self.source_code, "query": query, "error": str(result)},
                )
            else:
                batches.append(result)
        if not batches:
            raise RuntimeError("all EIS 44-FZ queries failed: " + "; ".join(map(str, errors)))
        return batches

    async def _fetch_query(self, client: httpx.AsyncClient, query: str) -> list[CollectedItem]:
        response = await request_with_retry(
            client,
            "GET",
            self.search_url,
            params={
                "searchString": query,
                "morphology": "on",
                "fz44": "on",
                "sortBy": "PUBLISH_DATE",
                "pageNumber": 1,
                "sortDirection": "false",
                "recordsPerPage": "_50",
            },
            attempts=self.retry_attempts,
            backoff_seconds=self.retry_backoff_seconds,
        )
        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> list[CollectedItem]:
        response.raise_for_status()
        text = response.text
        if "проверка безопасности" in text.casefold() or "captcha" in text.casefold():
            raise RuntimeError("EIS security verification page returned")
        soup = BeautifulSoup(text, "html.parser")
        items: list[CollectedItem] = []
        for card in soup.select("div.search-registry-entry-block"):
            item = self._parse_card(card)
            if item is not None:
                items.append(item)
        return items

    def _parse_card(self, card: Tag) -> CollectedItem | None:
        number_link = card.select_one(".registry-entry__header-mid__number a[href]")
        title_node = card.select_one(".registry-entry__body-value")
        if number_link is None or title_node is None:
            return None
        match = NUMBER_RE.search(number_link.get_text(" ", strip=True))
        href = number_link.get("href")
        title = title_node.get_text(" ", strip=True)
        if match is None or not isinstance(href, str) or not title:
            return None
        full_text = card.get_text(" ", strip=True)
        price_node = card.select_one(".price-block__value")
        customer_node = card.select_one(".registry-entry__body-href a")
        method_node = card.select_one(".registry-entry__header-top__title")
        dates = [node.get_text(" ", strip=True) for node in card.select(".data-block__value")]
        url = urljoin(self.base_url, href)
        payload: dict[str, Any] = {
            "title": title,
            "description": self._labeled_value(card, "Наименование объекта закупки") or title,
            "budget": price_node.get_text(" ", strip=True) if price_node else None,
            "customer": customer_node.get_text(" ", strip=True) if customer_node else None,
            "procurement_number": match.group("number"),
            "procurement_method": method_node.get_text(" ", strip=True) if method_node else None,
            "published_at": self._labeled_date(full_text, "Размещено")
            or (dates[0] if dates else None),
            "deadline_at": self._labeled_date(full_text, "Окончание подачи заявок"),
            "location": self._labeled_value(card, "Место нахождения"),
            "documentation_url": url,
            "law": "44-ФЗ",
        }
        return CollectedItem(external_id=match.group("number"), url=url, payload=payload)

    def normalize(self, item: CollectedItem) -> NormalizedOpportunity:
        title = self._text(item.payload.get("title"))
        if not title:
            raise ValueError(f"EIS notice {item.external_id!r} has no title")
        description = self._text(item.payload.get("description"))
        fingerprint = hashlib.sha256(
            "\n".join((title.casefold(), (description or "").casefold())).encode()
        ).hexdigest()
        return NormalizedOpportunity(
            external_id=item.external_id,
            title=title,
            description=description,
            source_category="44-ФЗ",
            url=item.url,
            budget_text=self._text(item.payload.get("budget")),
            published_at=self._date(item.payload.get("published_at")),
            deadline_at=self._date(item.payload.get("deadline_at")),
            fetched_at=item.fetched_at,
            customer_name=self._text(item.payload.get("customer")),
            customer_type="government",
            procurement_number=self._text(item.payload.get("procurement_number")),
            procurement_method=self._text(item.payload.get("procurement_method")),
            documentation_url=self._text(item.payload.get("documentation_url")),
            location=self._text(item.payload.get("location")),
            opportunity_type="tender",
            market="ru",
            fingerprint=fingerprint,
        )

    @staticmethod
    def _labeled_value(card: Tag, label: str) -> str | None:
        for node in card.select(".registry-entry__body-block"):
            text = node.get_text(" ", strip=True)
            if label.casefold() in text.casefold():
                value = node.select_one(".registry-entry__body-value, .registry-entry__body-href")
                if value is not None:
                    return value.get_text(" ", strip=True) or None
        return None

    @staticmethod
    def _labeled_date(text: str, label: str) -> str | None:
        remainder = text.casefold().partition(label.casefold())[2]
        match = DATE_RE.search(remainder[:100])
        return match.group(0) if match else None

    @staticmethod
    def _text(value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    @staticmethod
    def _date(value: Any) -> datetime | None:
        if not value:
            return None
        match = DATE_RE.search(str(value))
        if match is None:
            return None
        raw = match.group("date") + (f" {match.group('time')}" if match.group("time") else "")
        fmt = "%d.%m.%Y %H:%M" if match.group("time") else "%d.%m.%Y"
        return datetime.strptime(raw, fmt).replace(tzinfo=MOSCOW_TZ).astimezone(UTC)
