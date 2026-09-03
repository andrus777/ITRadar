from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from app.desktop.dialogs import OpportunityDialog
from app.desktop.services import (
    DashboardProvider,
    DeveloperProfileProvider,
    LocalCollectionRunner,
    MatchingProvider,
    OpportunityProvider,
    SourceProvider,
)
from app.desktop.views import (
    CollectionView,
    DashboardView,
    DeveloperProfileView,
    OpportunitiesView,
    SourcesView,
)


@dataclass(frozen=True, slots=True)
class NavigationItem:
    key: str
    label: str
    description: str
    icon: QStyle.StandardPixmap


NAVIGATION_ITEMS = (
    NavigationItem(
        "dashboard",
        "Dashboard",
        "Сводное состояние IT Radar",
        QStyle.StandardPixmap.SP_ComputerIcon,
    ),
    NavigationItem(
        "opportunities",
        "Opportunities",
        "Найденные возможности",
        QStyle.StandardPixmap.SP_FileDialogDetailedView,
    ),
    NavigationItem("sources", "Sources", "Источники данных", QStyle.StandardPixmap.SP_DriveNetIcon),
    NavigationItem(
        "collection", "Collection", "Управление сбором", QStyle.StandardPixmap.SP_BrowserReload
    ),
    NavigationItem(
        "profile",
        "Developer Profile",
        "Профиль разработчика",
        QStyle.StandardPixmap.SP_FileDialogInfoView,
    ),
    NavigationItem(
        "telegram", "Telegram", "Бот и дайджест", QStyle.StandardPixmap.SP_MessageBoxInformation
    ),
    NavigationItem("logs", "Logs", "Журнал работы", QStyle.StandardPixmap.SP_FileIcon),
    NavigationItem(
        "settings",
        "Settings",
        "Настройки приложения",
        QStyle.StandardPixmap.SP_FileDialogContentsView,
    ),
)


class PlaceholderView(QWidget):
    """Temporary page replaced by a feature view in subsequent commits."""

    def __init__(self, item: NavigationItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(f"{item.key}View")

        title = QLabel(item.label)
        title.setObjectName("pageTitle")
        description = QLabel(item.description)
        description.setObjectName("pageDescription")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()


class MainWindow(QMainWindow):
    """Main desktop shell shared by all IT Radar feature views."""

    def __init__(
        self,
        dashboard_provider: DashboardProvider | None = None,
        opportunity_provider: OpportunityProvider | None = None,
        source_provider: SourceProvider | None = None,
        collection_runner: LocalCollectionRunner | None = None,
        profile_provider: DeveloperProfileProvider | None = None,
        matching_provider: MatchingProvider | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle("IT Radar Desktop")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

        self.sidebar = self._build_navigation()
        self.workspace = QStackedWidget()
        self.workspace.setObjectName("workspace")
        self.dashboard_view = DashboardView(dashboard_provider)
        self.opportunity_provider = opportunity_provider
        self._opportunity_dialogs: list[OpportunityDialog] = []
        self.workspace.addWidget(self.dashboard_view)
        self.opportunities_view = OpportunitiesView(opportunity_provider)
        self.workspace.addWidget(self.opportunities_view)
        self.sources_view = SourcesView(source_provider)
        self.workspace.addWidget(self.sources_view)
        self.collection_view = CollectionView(source_provider, collection_runner)
        self.workspace.addWidget(self.collection_view)
        self.profile_view = DeveloperProfileView(profile_provider, matching_provider)
        self.workspace.addWidget(self.profile_view)
        for item in NAVIGATION_ITEMS[5:]:
            self.workspace.addWidget(PlaceholderView(item))

        shell = QWidget()
        shell.setObjectName("applicationShell")
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        shell_layout.addWidget(self.sidebar)
        shell_layout.addWidget(self.workspace, 1)
        self.setCentralWidget(shell)

        self.navigation_list.currentRowChanged.connect(self._open_page)
        self.dashboard_view.opportunity_activated.connect(self._open_opportunity)
        self.opportunities_view.opportunity_activated.connect(self._open_opportunity)
        self.navigation_list.setCurrentRow(0)
        self.setStatusBar(self._build_status_bar())

    def _build_navigation(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)

        brand = QLabel("IT RADAR")
        brand.setObjectName("brand")
        subtitle = QLabel("Desktop Console")
        subtitle.setObjectName("brandSubtitle")

        self.navigation_list = QListWidget()
        self.navigation_list.setObjectName("navigationList")
        self.navigation_list.setFrameShape(QFrame.Shape.NoFrame)
        self.navigation_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.navigation_list.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        for item in NAVIGATION_ITEMS:
            list_item = QListWidgetItem(item.label)
            list_item.setIcon(self.style().standardIcon(item.icon))
            list_item.setData(Qt.ItemDataRole.UserRole, item.key)
            self.navigation_list.addItem(list_item)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 16)
        layout.setSpacing(4)
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addSpacing(28)
        layout.addWidget(self.navigation_list)
        return sidebar

    def _build_status_bar(self) -> QStatusBar:
        status_bar = QStatusBar()
        status_bar.setObjectName("applicationStatusBar")
        status_bar.setSizeGripEnabled(False)
        status_bar.showMessage("Ready")

        version = QLabel("IT Radar v0.1.0")
        version.setObjectName("versionLabel")
        status_bar.addPermanentWidget(version)
        return status_bar

    def _open_page(self, index: int) -> None:
        if 0 <= index < self.workspace.count():
            self.workspace.setCurrentIndex(index)

    def _open_opportunity(self, opportunity_id: int) -> None:
        dialog = OpportunityDialog(opportunity_id, self.opportunity_provider, self)
        self._opportunity_dialogs.append(dialog)
        dialog.finished.connect(lambda: self._forget_dialog(dialog))
        dialog.status_changed.connect(
            lambda _opportunity_id, _status: self.opportunities_view.request_refresh()
        )
        dialog.show()
        dialog.request_load()

    def _forget_dialog(self, dialog: OpportunityDialog) -> None:
        if dialog in self._opportunity_dialogs:
            self._opportunity_dialogs.remove(dialog)
        dialog.deleteLater()
