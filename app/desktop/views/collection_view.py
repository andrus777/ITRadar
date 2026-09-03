import asyncio

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.desktop.services.background_worker import BackgroundWorker
from app.desktop.services.collection import (
    CollectionBatchResult,
    CollectionProgress,
    LocalCollectionRunner,
)
from app.desktop.services.sources import SourceProvider
from app.schemas.source_management import SourceSummary


class CollectionView(QWidget):
    columns = ("Run", "Source", "State", "Received", "New", "Duplicates", "Rejected", "Error")

    def __init__(
        self,
        provider: SourceProvider | None = None,
        runner: LocalCollectionRunner | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.provider, self.runner = provider, runner
        self.sources: list[SourceSummary] = []
        self.worker: BackgroundWorker | None = None
        self.setObjectName("collectionView")
        self._build_ui()

    def _build_ui(self) -> None:
        title, subtitle = QLabel("Collection"), QLabel("Ручной запуск и результаты сборщиков")
        title.setObjectName("pageTitle")
        subtitle.setObjectName("pageDescription")
        self.run_all_button, self.run_selected_button, self.stop_button = (
            QPushButton("RUN ALL"),
            QPushButton("RUN SELECTED"),
            QPushButton("STOP"),
        )
        self.run_all_button.setObjectName("primaryButton")
        self.run_selected_button.setObjectName("secondaryButton")
        self.stop_button.setObjectName("secondaryButton")
        self.run_all_button.clicked.connect(self.run_all)
        self.run_selected_button.clicked.connect(self.run_selected)
        self.stop_button.clicked.connect(self.stop)
        actions = QHBoxLayout()
        actions.addWidget(self.run_all_button)
        actions.addWidget(self.run_selected_button)
        actions.addWidget(self.stop_button)
        actions.addStretch()
        self.table = QTableWidget(0, len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.feedback = QLabel("Загрузка источников…")
        self.feedback.setObjectName("dashboardFeedback")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 28)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(actions)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.feedback)
        self._set_running(False)

    async def load(self) -> None:
        if self.provider is None:
            self.feedback.setText("Сервис источников не настроен")
            return
        try:
            self.set_sources(await self.provider.list_sources())
        except Exception:
            self.feedback.setText("Не удалось загрузить источники")

    def set_sources(self, sources: list[SourceSummary]) -> None:
        self.sources = sources
        self.table.setRowCount(len(sources))
        for row, source in enumerate(sources):
            values = (
                "",
                source.name,
                "ready" if source.enabled else "disabled",
                str(source.items_received),
                str(source.items_new),
                str(source.items_duplicate),
                str(source.items_rejected),
                source.last_error or "—",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, source.code)
                if column == 0:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Unchecked)
                self.table.setItem(row, column, item)
        self.feedback.setText(f"Готово к запуску: {len(self.runnable_codes())}")

    def runnable_codes(self) -> list[str]:
        return [
            source.code for source in self.sources if source.enabled and source.adapter_available
        ]

    def selected_codes(self) -> list[str]:
        return [
            self.sources[row].code
            for row in range(len(self.sources))
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked
            and self.sources[row].enabled
            and self.sources[row].adapter_available
        ]

    def run_all(self) -> None:
        self._start(self.runnable_codes())

    def run_selected(self) -> None:
        self._start(self.selected_codes())

    def _start(self, codes: list[str]) -> None:
        if self.worker is not None or self.runner is None:
            return
        if not codes:
            self.feedback.setText("Не выбраны доступные источники")
            return
        self.progress_bar.setRange(0, len(codes))
        self.progress_bar.setValue(0)
        self._set_running(True)
        self.worker = BackgroundWorker(lambda emit, cancel: self.runner.run(codes, emit, cancel))
        self.worker.signals.progress.connect(self._on_progress)
        self.worker.signals.result.connect(self._on_result)
        self.worker.signals.error.connect(self.feedback.setText)
        self.worker.signals.finished.connect(self._on_finished)
        QThreadPool.globalInstance().start(self.worker)

    def stop(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.feedback.setText("Остановка после текущего источника…")
            self.stop_button.setEnabled(False)

    def _on_progress(self, update: CollectionProgress) -> None:
        self.feedback.setText(f"{update.position}/{update.total}: {update.source} — {update.state}")
        if update.result is None:
            return
        self.progress_bar.setValue(update.position)
        for row, source in enumerate(self.sources):
            if source.code == update.source:
                result = update.result
                for column, value in enumerate(
                    (
                        result.status,
                        result.items_received,
                        result.items_new,
                        result.items_duplicate,
                        result.items_rejected,
                        result.error or "—",
                    ),
                    start=2,
                ):
                    self.table.item(row, column).setText(str(value))
                break

    def _on_result(self, result: CollectionBatchResult) -> None:
        suffix = " (остановлено)" if result.cancelled else ""
        self.feedback.setText(f"Завершено: {result.completed}/{result.total}{suffix}")

    def _on_finished(self) -> None:
        self.worker = None
        self._set_running(False)
        asyncio.create_task(self.load())

    def _set_running(self, running: bool) -> None:
        self.run_all_button.setEnabled(not running)
        self.run_selected_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.table.setEnabled(not running)
