import hashlib
import json
import re
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.collectors.base import CollectorAdapter
from app.http import request_with_retry
from app.schemas import CollectedItem, NormalizedOpportunity

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")
BUDGET_LINE_RE = re.compile(
    r"^(?:бюджет|оплата|зарплата|стоимость|гонорар)\s*[:—-]?\s*(?P<value>.+)$",
    re.IGNORECASE,
)


class TelegramChannelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    enabled: bool = True
    category: str = Field(pattern=r"^(?:freelance|projects)$")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        normalized = value.strip().lstrip("@")
        if not USERNAME_RE.fullmatch(normalized):
            raise ValueError("invalid public Telegram channel username")
        return normalized


def parse_telegram_whitelist(value: str) -> list[TelegramChannelConfig]:
    data = json.loads(value)
    if not isinstance(data, list):
        raise ValueError("Telegram source whitelist must be a JSON list")
    return [TelegramChannelConfig.model_validate(item) for item in data]


class TelegramChannelCollector(CollectorAdapter):
    """Collect message candidates from one explicitly allowed public channel."""

    source_type = "telegram"
    collection_method = "telegram"
    market = "ru"
    priority = "P1"

    def __init__(
        self,
        *,
        channel: TelegramChannelConfig,
        count: int = 20,
        timeout_seconds: float = 30,
        client: httpx.AsyncClient | None = None,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        if not 1 <= count <= 100:
            raise ValueError("count must be between 1 and 100")
        self.channel = channel
        self.count = count
        self.timeout_seconds = timeout_seconds
        self.client = client
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    @property
    def source_code(self) -> str:
        return f"telegram_{self.channel.username.casefold()}"

    @property
    def source_name(self) -> str:
        return f"Telegram @{self.channel.username}"

    @property
    def base_url(self) -> str:
        return f"https://t.me/{self.channel.username}"

    @property
    def endpoint(self) -> str:
        return f"https://t.me/s/{self.channel.username}"

    @property
    def default_opportunity_type(self) -> str:
        return "project" if self.channel.category == "projects" else "freelance"

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
            self.endpoint,
            attempts=self.retry_attempts,
            backoff_seconds=self.retry_backoff_seconds,
        )
        return self._parse_response(response)[-self.count :]

    def normalize(self, item: CollectedItem) -> NormalizedOpportunity:
        text = self._text(item.payload.get("text"))
        if not text:
            raise ValueError(f"Telegram post {item.external_id!r} has no text")
        title = self._title(text)
        fingerprint = hashlib.sha256(text.casefold().encode()).hexdigest()
        return NormalizedOpportunity(
            external_id=item.external_id,
            title=title,
            description=text,
            source_category=self.channel.category,
            url=item.url,
            budget_text=self._budget_text(text),
            published_at=self._date(item.payload.get("published_at")),
            fetched_at=item.fetched_at,
            opportunity_type=self.default_opportunity_type,
            market="ru",
            fingerprint=fingerprint,
        )

    def _parse_response(self, response: httpx.Response) -> list[CollectedItem]:
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        items: list[CollectedItem] = []
        for message in soup.select(".tgme_widget_message[data-post]"):
            item = self._parse_message(message)
            if item is not None:
                items.append(item)
        return items

    def _parse_message(self, message: Tag) -> CollectedItem | None:
        post = message.get("data-post")
        text_node = message.select_one(".tgme_widget_message_text")
        time_node = message.select_one(".tgme_widget_message_date time[datetime]")
        if not isinstance(post, str) or text_node is None:
            return None
        channel, separator, message_id = post.rpartition("/")
        if not separator or channel.casefold() != self.channel.username.casefold():
            return None
        text = text_node.get_text("\n", strip=True)
        if not text:
            return None
        payload: dict[str, Any] = {
            "channel": channel,
            "message_id": message_id,
            "category": self.channel.category,
            "text": text,
            "published_at": time_node.get("datetime") if time_node else None,
        }
        return CollectedItem(
            external_id=message_id,
            url=f"https://t.me/{channel}/{message_id}",
            payload=payload,
        )

    @staticmethod
    def _title(value: str) -> str:
        first_line = next((line.strip() for line in value.splitlines() if line.strip()), value)
        return first_line[:500]

    @staticmethod
    def _budget_text(value: str) -> str | None:
        for line in value.splitlines():
            match = BUDGET_LINE_RE.match(line.strip())
            if match:
                return match.group("value").strip() or None
        return None

    @staticmethod
    def _text(value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    @staticmethod
    def _date(value: Any) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
