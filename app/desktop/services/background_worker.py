from collections.abc import Callable
from threading import Event
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    progress = Signal(object)
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class BackgroundWorker(QRunnable):
    """Run blocking application work in QThreadPool with cooperative cancellation."""

    def __init__(self, function: Callable[[Callable[[Any], None], Event], Any]) -> None:
        super().__init__()
        self.function = function
        self.signals = WorkerSignals()
        self.cancel_event = Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            result = self.function(self.signals.progress.emit, self.cancel_event)
        except Exception:
            self.signals.error.emit("Фоновая операция завершилась ошибкой")
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
