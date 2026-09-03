import os
from datetime import UTC, datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt

from app.desktop.app import create_application
from app.desktop.views.collection_view import CollectionView
from app.schemas.source_management import SourceSummary


def source(code: str, *, enabled: bool = True, available: bool = True) -> SourceSummary:
    return SourceSummary(
        source_id=1,
        code=code,
        name=code,
        base_url="https://example.com",
        enabled=enabled,
        market="global",
        source_type="jobs",
        collection_method="api",
        priority="normal",
        poll_interval_minutes=60,
        health="ok",
        adapter_available=available,
        last_run_at=datetime.now(UTC),
        last_run_status=None,
        items_received=0,
        items_new=0,
        items_duplicate=0,
        items_rejected=0,
        last_error=None,
    )


def test_collection_view_filters_unrunnable_sources() -> None:
    create_application([])
    view = CollectionView()
    view.set_sources(
        [source("ready"), source("off", enabled=False), source("missing", available=False)]
    )
    assert view.runnable_codes() == ["ready"]


def test_collection_view_builds_selected_source_list() -> None:
    create_application([])
    view = CollectionView()
    view.set_sources([source("one"), source("two")])
    view.table.item(1, 0).setCheckState(Qt.CheckState.Checked)
    assert view.selected_codes() == ["two"]
