"""System tray icon and context menu."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QApplication

from core.logger import get_logger

if TYPE_CHECKING:
    from core.application import DevDeskApplication

logger = get_logger("tray")


class SystemTray(QSystemTrayIcon):
    """Primary entry point for DevDesk."""

    open_dashboard = Signal()
    open_jira = Signal()
    open_pull_requests = Signal()
    open_working_time = Signal()
    open_quick_access = Signal()
    open_developer_tools = Signal()
    open_settings = Signal()
    refresh_all = Signal()
    exit_requested = Signal()

    def __init__(self, app: "DevDeskApplication", parent=None) -> None:
        super().__init__(parent)
        self._app = app
        self._build_icon()
        self._build_menu()
        self.setToolTip("DevDesk")
        self.activated.connect(self._on_activated)
        self.show()
        logger.info("System tray icon initialized")

    def _build_icon(self) -> None:
        # Use a standard icon for now; custom icons can be added later
        icon = QIcon.fromTheme("applications-development")
        if icon.isNull():
            # Fallback: create a simple pixmap-based icon
            from PySide6.QtGui import QPixmap, QPainter, QColor, QFont

            pix = QPixmap(64, 64)
            pix.fill(QColor(0, 120, 212))
            painter = QPainter(pix)
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Sans", 28, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(pix.rect(), 0x84, "D")  # AlignCenter
            painter.end()
            icon = QIcon(pix)
        self.setIcon(icon)

    def _build_menu(self) -> None:
        menu = QMenu()

        act_dashboard = QAction("Open Dashboard", self)
        act_dashboard.triggered.connect(self.open_dashboard.emit)
        menu.addAction(act_dashboard)

        menu.addSeparator()

        act_jira = QAction("Jira Tasks", self)
        act_jira.triggered.connect(self.open_jira.emit)
        menu.addAction(act_jira)

        act_prs = QAction("Pull Requests", self)
        act_prs.triggered.connect(self.open_pull_requests.emit)
        menu.addAction(act_prs)

        act_wt = QAction("Working Time", self)
        act_wt.triggered.connect(self.open_working_time.emit)
        menu.addAction(act_wt)

        act_qa = QAction("Quick Access", self)
        act_qa.triggered.connect(self.open_quick_access.emit)
        menu.addAction(act_qa)

        act_tools = QAction("Developer Tools", self)
        act_tools.triggered.connect(self.open_developer_tools.emit)
        menu.addAction(act_tools)

        menu.addSeparator()

        act_refresh = QAction("Refresh All", self)
        act_refresh.triggered.connect(self.refresh_all.emit)
        menu.addAction(act_refresh)

        act_settings = QAction("Settings", self)
        act_settings.triggered.connect(self.open_settings.emit)
        menu.addAction(act_settings)

        menu.addSeparator()

        act_exit = QAction("Exit", self)
        act_exit.triggered.connect(self.exit_requested.emit)
        menu.addAction(act_exit)

        self.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_dashboard.emit()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click – also open on some platforms
            pass

    def update_tooltip(self, text: str) -> None:
        self.setToolTip(f"DevDesk – {text}")

    def is_available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()
