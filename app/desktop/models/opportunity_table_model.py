from datetime import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from app.schemas.opportunity_management import OpportunityListItem


class OpportunityTableModel(QAbstractTableModel):
    columns = (
        ("score", "Score"),
        ("title", "Title"),
        ("source", "Source"),
        ("opportunity_type", "Type"),
        ("category", "Category"),
        ("technologies", "Technologies"),
        ("budget", "Budget"),
        ("published_at", "Published"),
        ("status", "Status"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.items: list[OpportunityListItem] = []

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self.items)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self.columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self.items):
            return None
        item = self.items[index.row()]
        field = self.columns[index.column()][0]
        value = getattr(item, field)
        if role == Qt.ItemDataRole.UserRole:
            return item.opportunity_id
        if role == Qt.ItemDataRole.DisplayRole:
            return self._display(field, value)
        if role == Qt.ItemDataRole.ForegroundRole and field == "score":
            return self._score_color(item.score)
        if role == Qt.ItemDataRole.TextAlignmentRole and field == "score":
            return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._tooltip(item)
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
            and 0 <= section < len(self.columns)
        ):
            return self.columns[section][1]
        return None

    def set_items(self, items: list[OpportunityListItem]) -> None:
        self.beginResetModel()
        self.items = items
        self.endResetModel()

    def opportunity_id(self, row: int) -> int | None:
        return self.items[row].opportunity_id if 0 <= row < len(self.items) else None

    @staticmethod
    def _display(field: str, value: object) -> str:
        if value is None:
            return "—"
        if field == "score":
            return f"{value}%"
        if field == "technologies":
            return ", ".join(value) if isinstance(value, list) else str(value)
        if field == "published_at" and isinstance(value, datetime):
            return value.astimezone().strftime("%d.%m.%Y %H:%M")
        return str(value)

    @staticmethod
    def _score_color(score: int | None) -> QColor:
        if score is None:
            return QColor("#8e98aa")
        if score >= 90:
            return QColor("#43c781")
        if score >= 80:
            return QColor("#75b7ff")
        if score >= 70:
            return QColor("#f0b44c")
        return QColor("#8e98aa")

    @staticmethod
    def _tooltip(item: OpportunityListItem) -> str:
        return f"{item.title}\nИсточник: {item.source}\nРынок: {item.market}"
