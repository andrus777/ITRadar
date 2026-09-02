import json
import logging

from app.logging import JsonFormatter


def test_json_log_contains_collection_context() -> None:
    record = logging.LogRecord(
        name="collector",
        level=logging.ERROR,
        pathname=__file__,
        lineno=10,
        msg="collection fetch failed",
        args=(),
        exc_info=None,
    )
    record.run_id = 42
    record.source = "jobicy"
    record.error = "temporary failure"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "ERROR"
    assert payload["run_id"] == 42
    assert payload["source"] == "jobicy"
    assert payload["error"] == "temporary failure"
