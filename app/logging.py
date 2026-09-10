import json
import logging
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Any

RESERVED = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


@dataclass(frozen=True, slots=True)
class LogEntry:
    timestamp: datetime
    level: str
    logger: str
    message: str
    source: str | None = None
    run_id: int | None = None


class LogBufferHandler(logging.Handler):
    """Keep a bounded log history and notify thread-safe UI bridges."""

    def __init__(self, capacity: int = 2_000) -> None:
        super().__init__()
        self.entries: deque[LogEntry] = deque(maxlen=capacity)
        self.listeners: list[Callable[[LogEntry], None]] = []
        self.lock = RLock()

    def emit(self, record: logging.LogRecord) -> None:
        entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created, UTC),
            level=record.levelname,
            logger=record.name,
            message=record.getMessage(),
            source=self._text(getattr(record, "source", None)),
            run_id=self._integer(getattr(record, "run_id", None)),
        )
        with self.lock:
            self.entries.append(entry)
            listeners = tuple(self.listeners)
        for listener in listeners:
            try:
                listener(entry)
            except RuntimeError:
                continue

    def snapshot(self) -> list[LogEntry]:
        with self.lock:
            return list(self.entries)

    def subscribe(self, listener: Callable[[LogEntry], None]) -> None:
        with self.lock:
            if listener not in self.listeners:
                self.listeners.append(listener)

    def unsubscribe(self, listener: Callable[[LogEntry], None]) -> None:
        with self.lock:
            if listener in self.listeners:
                self.listeners.remove(listener)

    @staticmethod
    def _text(value: object) -> str | None:
        return str(value) if value is not None else None

    @staticmethod
    def _integer(value: object) -> int | None:
        return value if isinstance(value, int) else None


desktop_log_buffer = LogBufferHandler()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(
            (key, value)
            for key, value in record.__dict__.items()
            if key not in RESERVED and not key.startswith("_")
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", *, capture_for_desktop: bool = False) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    if capture_for_desktop:
        root.addHandler(desktop_log_buffer)
    root.setLevel(level.upper())
