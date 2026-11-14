"""Global search dialog – searches local cache and shortcuts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from core.application import DevDeskApplication

from core.logger import get_logger

logger = get_logger("search")


class SearchDialog(QDialog):
    """Compact search-first interface over local data."""

    result_activated = Signal(str, str)  # kind, id_or_url

    def __init__(self, app: "DevDeskApplication", parent=None) -> None:
        super().__init__(parent)
        self._app = app
        self.setWindowTitle("Search – DevDesk")
        self.setMinimumSize(520, 360)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self._build()
        QShortcut(QKeySequence("Escape"), self, activated=self.reject)

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Search issues, PRs, shortcuts, projects…")
        self.input.textChanged.connect(self._on_query)
        self.input.returnPressed.connect(self._activate_current)
        layout.addWidget(self.input)

        self.list = QListWidget()
        self.list.itemActivated.connect(self._on_item_activated)
        self.list.itemDoubleClicked.connect(self._on_item_activated)
        layout.addWidget(self.list, stretch=1)

        self.hint = QLabel("Type to search local cache. Enter to open.")
        self.hint.setObjectName("cardSubtitle")
        layout.addWidget(self.hint)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.input.clear()
        self.input.setFocus()
        self._on_query("")

    def _on_query(self, text: str) -> None:
        self.list.clear()
        q = text.strip().lower()
        results: list[tuple[str, str, str, str]] = []  # kind, id, title, subtitle

        # Quick Access
        try:
            from services.quick_access import QuickAccessService

            qa = QuickAccessService(storage=self._app.storage)
            for sc in qa.search(q) if q else qa.shortcuts[:15]:
                results.append(("shortcut", sc.id, sc.name, f"{sc.type} · {sc.path}"))
        except Exception as exc:
            logger.debug("QA search error: %s", exc)

        # Jira cache
        try:
            cache = self._app.storage.load_cache("jira")
            issues = (cache.get("data") or {}).get("issues") or cache.get("data") or []
            if isinstance(issues, list):
                for issue in issues:
                    if not isinstance(issue, dict):
                        continue
                    key = issue.get("key", "")
                    summary = issue.get("fields", {}).get("summary") or issue.get("summary", "")
                    blob = f"{key} {summary}".lower()
                    if not q or q in blob:
                        results.append(("jira", key, f"{key}: {summary}", "Jira"))
        except Exception as exc:
            logger.debug("Jira cache search error: %s", exc)

        # GitHub PR cache
        try:
            cache = self._app.storage.load_cache("github")
            prs = (cache.get("data") or {}).get("pull_requests") or cache.get("data") or []
            if isinstance(prs, list):
                for pr in prs:
                    if not isinstance(pr, dict):
                        continue
                    title = pr.get("title", "")
                    number = pr.get("number", "")
                    repo = pr.get("repository", pr.get("repo", ""))
                    blob = f"{title} {number} {repo}".lower()
                    if not q or q in blob:
                        results.append(
                            ("github", str(pr.get("html_url") or pr.get("url") or number),
                             f"PR #{number}: {title}", f"GitHub · {repo}")
                        )
        except Exception as exc:
            logger.debug("GitHub cache search error: %s", exc)

        # Bitbucket PR cache
        try:
            cache = self._app.storage.load_cache("bitbucket")
            prs = (cache.get("data") or {}).get("pull_requests") or cache.get("data") or []
            if isinstance(prs, list):
                for pr in prs:
                    if not isinstance(pr, dict):
                        continue
                    title = pr.get("title", "")
                    number = pr.get("id") or pr.get("number", "")
                    repo = pr.get("destination", {}).get("repository", {}).get("full_name") or pr.get("repo", "")
                    blob = f"{title} {number} {repo}".lower()
                    if not q or q in blob:
                        link = pr.get("links", {}).get("html", {}).get("href") or str(number)
                        results.append(
                            ("bitbucket", str(link), f"PR #{number}: {title}", f"Bitbucket · {repo}")
                        )
        except Exception as exc:
            logger.debug("Bitbucket cache search error: %s", exc)

        for kind, rid, title, subtitle in results[:40]:
            item = QListWidgetItem(f"{title}\n  {subtitle}")
            item.setData(Qt.ItemDataRole.UserRole, (kind, rid))
            self.list.addItem(item)

        self.hint.setText(f"{self.list.count()} result(s)")

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind, rid = data
        self._open_result(kind, rid)
        self.accept()

    def _activate_current(self) -> None:
        item = self.list.currentItem() or (self.list.item(0) if self.list.count() else None)
        if item:
            self._on_item_activated(item)

    def _open_result(self, kind: str, rid: str) -> None:
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        from core.platform import Platform

        if kind == "shortcut":
            try:
                from services.quick_access import QuickAccessService

                QuickAccessService(storage=self._app.storage).open(rid)
            except Exception as exc:
                logger.error("Open shortcut failed: %s", exc)
        elif kind == "jira":
            base = self._app.config.get("jira.base_url", "").rstrip("/")
            if base and rid:
                QDesktopServices.openUrl(QUrl(f"{base}/browse/{rid}"))
        elif kind in ("github", "bitbucket"):
            if rid.startswith("http"):
                QDesktopServices.openUrl(QUrl(rid))
        self.result_activated.emit(kind, rid)
