from app.desktop.services.background_worker import BackgroundWorker


def test_background_worker_reports_progress_result_and_finish() -> None:
    events: list[object] = []
    worker = BackgroundWorker(lambda progress, _cancel: (progress("half"), 42)[1])
    worker.signals.progress.connect(events.append)
    worker.signals.result.connect(events.append)
    worker.signals.finished.connect(lambda: events.append("finished"))
    worker.run()
    assert events == ["half", 42, "finished"]


def test_background_worker_exposes_cooperative_cancellation() -> None:
    worker = BackgroundWorker(lambda _progress, cancel: cancel.is_set())
    results: list[bool] = []
    worker.signals.result.connect(results.append)
    worker.cancel()
    worker.run()
    assert results == [True]
