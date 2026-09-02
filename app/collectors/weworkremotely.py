import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import httpx
from bs4 import BeautifulSoup

from app.collectors.base import CollectorAdapter
from app.http import request_with_retry
from app.schemas import CollectedItem, NormalizedOpportunity


class WeWorkRemotelyCollector(CollectorAdapter):
    """Collect programming opportunities from We Work Remotely's public RSS feed."""

    source_code = "weworkremotely"
    source_name = "We Work Remotely"
    base_url = "https://weworkremotely.com"
    endpoint = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    market = "international"
    priority = "P2"
    source_type = "rss"
    collection_method = "rss"
    default_opportunity_type = "vacancy"

    def __init__(
        self,
        *,
        count: int = 20,
        timeout_seconds: float = 30,
        client: httpx.AsyncClient | None = None,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        if not 1 <= count <= 100:
            raise ValueError("count must be between 1 and 100")
        self.count = count
        self.timeout_seconds = timeout_seconds
        self.client = client
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    async def fetch(self) -> list[CollectedItem]:
        if self.client is not None:
            response = await request_with_retry(
                self.client,
                "GET",
                self.endpoint,
                attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )
        else:
            headers = {
                "Accept": "application/rss+xml, application/xml",
                "User-Agent": "ITRadar/0.1 (+https://github.com/andrus777/ITRadar)",
            }
            async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers) as client:
                response = await request_with_retry(
                    client,
                    "GET",
                    self.endpoint,
                    attempts=self.retry_attempts,
                    backoff_seconds=self.retry_backoff_seconds,
                )
        return self._parse_response(response)[: self.count]

    def normalize(self, item: CollectedItem) -> NormalizedOpportunity:
        raw_title = str(item.payload.get("title") or "").strip()
        if not raw_title:
            raise ValueError(f"WWR item {item.external_id!r} has no title")
        company, separator, role = raw_title.partition(":")
        title = role.strip() if separator and role.strip() else raw_title
        customer = company.strip() if separator and company.strip() else None
        description_html = str(item.payload.get("description") or "").strip()
        description = (
            BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True)
            if description_html
            else None
        )
        fingerprint_source = "\n".join((title.casefold(), description or "", item.url))

        return NormalizedOpportunity(
            external_id=item.external_id,
            title=title,
            description=description,
            url=item.url,
            published_at=self._datetime(item.payload.get("pubDate")),
            fetched_at=item.fetched_at,
            customer_name=customer,
            location=str(item.payload.get("region") or "").strip() or None,
            remote=True,
            fingerprint=hashlib.sha256(fingerprint_source.encode()).hexdigest(),
        )

    @staticmethod
    def _parse_response(response: httpx.Response) -> list[CollectedItem]:
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items: list[CollectedItem] = []
        for node in root.findall("./channel/item"):
            payload = {
                "title": node.findtext("title"),
                "description": node.findtext("description"),
                "pubDate": node.findtext("pubDate"),
                "region": node.findtext("region"),
                "category": node.findtext("category"),
            }
            link = (node.findtext("link") or "").strip()
            guid = (node.findtext("guid") or link).strip()
            if not link or not guid:
                raise ValueError("WWR item requires guid and link")
            external_id = guid if len(guid) <= 255 else hashlib.sha256(guid.encode()).hexdigest()
            items.append(CollectedItem(external_id=external_id, url=link, payload=payload))
        return items

    @staticmethod
    def _datetime(value: object) -> datetime | None:
        if value in (None, ""):
            return None
        return parsedate_to_datetime(str(value))
