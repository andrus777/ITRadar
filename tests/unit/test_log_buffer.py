import logging

from app.logging import LogBufferHandler


def record(message: str, *, level: int = logging.INFO, source: str | None = None):
    item = logging.LogRecord("app.collector", level, __file__, 1, message, (), None)
    if source is not None:
        item.source = source
    item.run_id = 42
    return item


def test_log_buffer_is_bounded_and_notifies_subscribers() -> None:
    handler = LogBufferHandler(capacity=2)
    received = []
    handler.subscribe(received.append)

    handler.emit(record("one"))
    handler.emit(record("two", level=logging.WARNING, source="workspace"))
    handler.emit(record("three", level=logging.ERROR))

    assert [entry.message for entry in handler.snapshot()] == ["two", "three"]
    assert [entry.message for entry in received] == ["one", "two", "three"]
    assert received[1].source == "workspace"
    assert received[1].run_id == 42

    handler.unsubscribe(received.append)
    handler.emit(record("four"))
    assert len(received) == 3
