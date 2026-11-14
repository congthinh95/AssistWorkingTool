"""Main application window with navigation and stacked pages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QWidget,
)

from core.logger import get_logger
from ui.styles import get_stylesheet
from ui.pages.overview import OverviewPage
from ui.pages.jira import JiraPage
from ui.pages.pull_requests import PullRequestsPage
from ui.pages.working_time import WorkingTimePage
from ui.pages.quick_access import QuickAccessPage
from ui.pages.developer_tools import DeveloperToolsPage
from ui.pages.settings import SettingsPage
from ui.search_dialog import SearchDialog

if TYPE_CHECKING:
    from core.application import DevDeskApplication

logger = get_logger("main_window")

NAV_ITEMS = [
    ("Dashboard", 0),
    ("Jira", 1),
    ("Pull Requests", 2),
    ("Working Time", 3),
    ("Quick Access", 4),
    ("Developer Tools", 5),
    ("Settings", 6),
]


class MainWindow(QMainWindow):
    """Primary dashboard window. Closing hides to tray instead of quitting."""

    def __init__(self, app: "DevDeskApplication") -> None:
        super().__init__()
        self._app = app
        self._search_dialog: Optional[SearchDialog] = None
        self.setWindowTitle("DevDesk")
        self.setMinimumSize(860, 560)
        self.resize(980, 640)

        self._apply_theme()
        self._build_ui()
        self._connect_shortcuts()
        self._connect_tray()

        logger.info("Main window created")

    def _apply_theme(self) -> None:
        theme = self._app.config.theme
        self.setStyleSheet(get_stylesheet(theme))

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(180)
        self.nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for label, _ in NAV_ITEMS:
            self.nav.addItem(QListWidgetItem(label))
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(self._on_nav_changed)
        layout.addWidget(self.nav)

        self.stack = QStackedWidget()
        self.page_overview = OverviewPage(self._app)
        self.page_jira = JiraPage(self._app)
        self.page_prs = PullRequestsPage(self._app)
        self.page_working_time = WorkingTimePage(self._app)
        self.page_quick_access = QuickAccessPage(self._app)
        self.page_dev_tools = DeveloperToolsPage(self._app)
        self.page_settings = SettingsPage(self._app)

        for page in (
            self.page_overview,
            self.page_jira,
            self.page_prs,
            self.page_working_time,
            self.page_quick_access,
            self.page_dev_tools,
            self.page_settings,
        ):
            self.stack.addWidget(page)

        layout.addWidget(self.stack, stretch=1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    def _connect_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self.show_page(0))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self.show_page(1))
        QShortcut(QKeySequence("Ctrl+3"), self, activated=lambda: self.show_page(2))
        QShortcut(QKeySequence("Ctrl+4"), self, activated=lambda: self.show_page(3))
        QShortcut(QKeySequence("Ctrl+5"), self, activated=lambda: self.show_page(4))
        QShortcut(QKeySequence("Ctrl+,"), self, activated=lambda: self.show_page(6))
        QShortcut(QKeySequence("Ctrl+K"), self, activated=self.open_search)
        QShortcut(QKeySequence("Ctrl+Shift+F"), self, activated=self.open_search)

    def _connect_tray(self) -> None:
        tray = self._app.tray
        if tray is None:
            return
        tray.open_dashboard.connect(self.show_and_raise)
        tray.open_jira.connect(lambda: self._show_and_navigate(1))
        tray.open_pull_requests.connect(lambda: self._show_and_navigate(2))
        tray.open_working_time.connect(lambda: self._show_and_navigate(3))
        tray.open_quick_access.connect(lambda: self._show_and_navigate(4))
        tray.open_developer_tools.connect(lambda: self._show_and_navigate(5))
        tray.open_settings.connect(lambda: self._show_and_navigate(6))
        tray.exit_requested.connect(self._app.shutdown)
        tray.refresh_all.connect(self._on_refresh_all)

    def open_search(self) -> None:
        if self._search_dialog is None:
            self._search_dialog = SearchDialog(self._app, self)
        self._search_dialog.show()
        self._search_dialog.raise_()
        self._search_dialog.activateWindow()

    def show_page(self, index: int) -> None:
        if 0 <= index < self.stack.count():
            self.nav.setCurrentRow(index)
            self.stack.setCurrentIndex(index)

    def _show_and_navigate(self, index: int) -> None:
        self.show_and_raise()
        self.show_page(index)

    @Slot()
    def show_and_raise(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_nav_changed(self, row: int) -> None:
        if row >= 0:
            self.stack.setCurrentIndex(row)

    def _on_refresh_all(self) -> None:
        if self._app.sync_service:
            self.status.showMessage("Refreshing all integrations…", 3000)
            self._app.sync_service.sync_all()
        else:
            self.status.showMessage("Sync service not ready", 3000)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._app.config.minimize_on_close:
            event.ignore()
            self.hide()
            logger.debug("Window hidden to tray")
        else:
            event.accept()
            self._app.shutdown()
