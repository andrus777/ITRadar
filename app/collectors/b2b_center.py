import hashlib
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup, Tag

from app.collectors.procurement import ProcurementCollectorAdapter
from app.http import request_with_retry
from app.schemas import CollectedItem, NormalizedOpportunity

DEFAULT_FEED_URL = "https://www.b2b-center.ru/search-tender/tendery-programmnoe-obespechenie/"
TENDER_ID_RE = re.compile(r"/(?:tender|tenders)-(?P<id>\d+)/")
TENDER_NUMBER_RE = re.compile(r"Тендер\s*№\s*(?P<number>\d+)", re.IGNORECASE)
DATE_FORMAT = "%d.%m.%Y %H:%M"
MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class B2BCenterCollector(ProcurementCollectorAdapter):
    """Collect public Russian software tenders from B2B-Center."""

    source_code = "b2b_center"
    source_name = "B2B-Center"
    base_url = "https://www.b2b-center.ru"

    def __init__(
        self,
        *,
        count: int = 50,
        feed_url: str = DEFAULT_FEED_URL,
        timeout_seconds: float = 30,
        client: httpx.AsyncClient | None = None,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        if not 1 <= count <= 200:
            raise ValueError("count must be between 1 and 200")
        self.count = count
        self.feed_url = feed_url
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
        title = self._text(item.payload.get("title"))
        if not title:
            raise ValueError(f"B2B-Center tender {item.external_id!r} has no title")
        description = self._text(item.payload.get("description"))
        fingerprint = hashlib.sha256(
            "\n".join((title.casefold(), (description or "").casefold())).encode()
        ).hexdigest()
        return NormalizedOpportunity(
            external_id=item.external_id,
            title=title,
            description=description,
            source_category=self._text(item.payload.get("category")),
            url=item.url,
            published_at=self._date(item.payload.get("published_at")),
            deadline_at=self._date(item.payload.get("deadline_at")),
            fetched_at=item.fetched_at,
            customer_name=self._text(item.payload.get("customer")),
            customer_type="business",
            procurement_number=self._text(item.payload.get("procurement_number")),
            procurement_method=self._text(item.payload.get("procurement_method")),
            documentation_url=self._text(item.payload.get("documentation_url")),
            opportunity_type="tender",
            market="ru",
            fingerprint=fingerprint,
        )

    def _parse_response(self, response: httpx.Response) -> list[CollectedItem]:
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        items: list[CollectedItem] = []
        seen: set[str] = set()
        for link in soup.select('a.search-results-title[href*="/market/"]'):
            item = self._parse_link(link)
            if item is not None and item.external_id not in seen:
                seen.add(item.external_id)
                items.append(item)
        return items

    def _parse_link(self, link: Tag) -> CollectedItem | None:
        href = link.get("href")
        row = link.find_parent("tr")
        if not isinstance(href, str) or row is None:
            return None
        id_match = TENDER_ID_RE.search(href)
        number_match = TENDER_NUMBER_RE.search(link.get_text(" ", strip=True))
        if id_match is None or number_match is None:
            return None
        desc_node = link.select_one(".search-results-title-desc")
        if desc_node is None:
            return None
        method_node = desc_node.select_one(".search-results-title-type")
        method = None
        if method_node is not None:
            method = method_node.get_text(" ", strip=True).partition(":")[2].strip() or None
        preview = self._description_without_method(desc_node)
        title = self._preview_title(preview)
        cells = row.find_all("td", recursive=False)
        dates = [cell.get_text(" ", strip=True) for cell in row.select("td.nowrap")]
        customer_link = row.select_one('a[href^="/firms/"]')
        category = cells[0].get_text(" ", strip=True).partition("Тендер №")[0].strip()
        canonical_url = self._canonical_url(urljoin(self.base_url, href))
        payload: dict[str, Any] = {
            "title": title,
            "description": preview or None,
            "category": category or None,
            "procurement_number": number_match.group("number"),
            "procurement_method": method,
            "customer": customer_link.get_text(" ", strip=True) if customer_link else None,
            "published_at": dates[0] if dates else None,
            "deadline_at": dates[1] if len(dates) > 1 else None,
            "documentation_url": canonical_url,
        }
        return CollectedItem(
            external_id=id_match.group("id"),
            url=canonical_url,
            payload=payload,
        )

    @staticmethod
    def _description_without_method(node: Tag) -> str:
        parts = [
            text.strip()
            for child in node.children
            if not (
                isinstance(child, Tag) and "search-results-title-type" in child.get("class", [])
            )
            for text in [child.get_text(" ", strip=True) if isinstance(child, Tag) else str(child)]
            if text.strip()
        ]
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    @staticmethod
    def _preview_title(value: str) -> str:
        words = value.split()
        if len(words) % 2 == 0 and words[: len(words) // 2] == words[len(words) // 2 :]:
            words = words[: len(words) // 2]
        return " ".join(words)[:500].strip()

    @staticmethod
    def _canonical_url(value: str) -> str:
        parts = urlsplit(value)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))

    @staticmethod
    def _text(value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    @staticmethod
    def _date(value: Any) -> datetime | None:
        if not value:
            return None
        return datetime.strptime(str(value), DATE_FORMAT).replace(tzinfo=MOSCOW_TZ).astimezone(UTC)
