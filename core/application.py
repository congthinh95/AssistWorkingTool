"""Main application class and single-instance guard."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QSharedMemory, QSystemSemaphore, Signal
from PySide6.QtWidgets import QApplication, QMessageBox

from .config import Config
from .logger import get_logger, setup_logging
from .platform import Platform
from .storage import Storage
from .credential_manager import CredentialManager

if TYPE_CHECKING:
    from services.sync import SyncService
    from services.notifications import NotificationService

logger = get_logger("application")

APP_NAME = "DevDesk"
APP_VERSION = "0.2.0"
ORGANIZATION = "DevDesk"


class SingleInstanceGuard:
    """Prevent multiple running instances using Qt shared memory."""

    def __init__(self, key: str = "DevDesk_SingleInstance") -> None:
        self._key = key
        self._semaphore = QSystemSemaphore(f"{key}_sem", 1)
        self._shared = QSharedMemory(key)
        self._is_running = False

    def try_lock(self) -> bool:
        self._semaphore.acquire()
        try:
            if self._shared.attach():
                self._shared.detach()
                self._is_running = True
                return False
            if not self._shared.create(1):
                self._is_running = True
                return False
            self._is_running = False
            return True
        finally:
            self._semaphore.release()

    def release(self) -> None:
        if self._shared.isAttached():
            self._shared.detach()


class DevDeskApplication(QApplication):
    """Custom QApplication holding shared services."""

    show_dashboard_requested = Signal()

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.setApplicationName(APP_NAME)
        self.setApplicationVersion(APP_VERSION)
        self.setOrganizationName(ORGANIZATION)
        self.setQuitOnLastWindowClosed(False)

        self._guard = SingleInstanceGuard()
        if not self._guard.try_lock():
            QMessageBox.warning(
                None,
                APP_NAME,
                "DevDesk is already running.\nCheck the system tray.",
            )
            sys.exit(0)

        self.platform = Platform()
        self.storage = Storage()
        setup_logging(log_dir=self.storage.logs_dir)
        logger.info("Starting %s v%s on %s", APP_NAME, APP_VERSION, Platform.get_platform_name())

        self.config = Config(self.storage)
        self.credentials = CredentialManager()

        self.main_window = None
        self.tray = None
        self.sync_service: Optional["SyncService"] = None
        self.notification_service: Optional["NotificationService"] = None

    def init_services(self) -> None:
        """Called after tray/window exist so notifications can use the tray."""
        from services.notifications import NotificationService
        from services.sync import SyncService

        self.notification_service = NotificationService(
            storage=self.storage,
            tray=self.tray,
            config=self.config.raw,
        )
        self.sync_service = SyncService(
            config=self.config,
            storage=self.storage,
            credentials=self.credentials,
            notifications=self.notification_service,
            parent=self,
        )
        self.sync_service.status_changed.connect(self._on_sync_status)
        self.sync_service.data_updated.connect(self._on_data_updated)
        self.sync_service.start()

    def _on_sync_status(self, message: str) -> None:
        if self.main_window and hasattr(self.main_window, "status"):
            self.main_window.status.showMessage(message, 4000)

    def _on_data_updated(self, name: str) -> None:
        if not self.main_window:
            return
        if name == "jira" and hasattr(self.main_window, "page_jira"):
            self.main_window.page_jira.reload_from_cache()
            self._update_overview_cards()
        elif name in ("github", "bitbucket") and hasattr(self.main_window, "page_prs"):
            self.main_window.page_prs.reload_from_cache()
            self._update_overview_cards()

    def _update_overview_cards(self) -> None:
        if not self.main_window or not hasattr(self.main_window, "page_overview"):
            return
        ov = self.main_window.page_overview
        jira = self.storage.load_cache("jira").get("data") or {}
        if hasattr(ov, "card_jira") and jira.get("count") is not None:
            ov.card_jira.set_value(str(jira.get("count", "—")), f"{jira.get('overdue_count', 0)} overdue")
            ov.card_overdue.set_value(str(jira.get("overdue_count", "—")), "")
        gh = self.storage.load_cache("github").get("data") or {}
        bb = self.storage.load_cache("bitbucket").get("data") or {}
        review = (gh.get("review_count") or 0) + (bb.get("review_count") or 0)
        mine = (gh.get("my_count") or 0) + (bb.get("my_count") or 0)
        if hasattr(ov, "card_pr_review"):
            ov.card_pr_review.set_value(str(review), "GitHub + Bitbucket")
            ov.card_my_prs.set_value(str(mine), "")

    def shutdown(self) -> None:
        logger.info("Shutting down DevDesk")
        if self.sync_service:
            self.sync_service.stop()
        self._guard.release()
        self.quit()
