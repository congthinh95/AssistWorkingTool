"""Pull Requests page – GitHub + Bitbucket."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from core.application import DevDeskApplication


class PullRequestsPage(QWidget):
    def __init__(self, app: "DevDeskApplication", parent=None) -> None:
        super().__init__(parent)
        self._app = app
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Pull Requests")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        header.addWidget(title)
        header.addStretch()

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._refresh)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        self.lbl_status = QLabel("Configure GitHub / Bitbucket in Settings.")
        self.lbl_status.setObjectName("cardSubtitle")
        layout.addWidget(self.lbl_status)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Source", "PR", "Title", "Repo", "Author", "Updated"]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._open_selected)
        layout.addWidget(self.table, stretch=1)

        self.reload_from_cache()

    def reload_from_cache(self) -> None:
        prs: list[dict[str, Any]] = []
        gh = self._app.storage.load_cache("github")
        gh_data = gh.get("data") or {}
        for pr in gh_data.get("pull_requests") or []:
            prs.append(pr)

        bb = self._app.storage.load_cache("bitbucket")
        bb_data = bb.get("data") or {}
        for pr in bb_data.get("pull_requests") or []:
            prs.append(pr)

        self._populate(prs)
        review = (gh_data.get("review_count") or 0) + (bb_data.get("review_count") or 0)
        mine = (gh_data.get("my_count") or 0) + (bb_data.get("my_count") or 0)
        if prs:
            self.lbl_status.setText(f"{len(prs)} PR(s) · {review} to review · {mine} mine")
        else:
            self.lbl_status.setText("No PRs cached. Enable integrations in Settings and refresh.")

    def _populate(self, prs: list[dict[str, Any]]) -> None:
        self.table.setRowCount(0)
        for pr in prs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                pr.get("source", ""),
                f"#{pr.get('number', '')}",
                pr.get("title", ""),
                pr.get("repository", ""),
                pr.get("user", ""),
                (pr.get("updated_at") or "")[:19].replace("T", " "),
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setData(Qt.ItemDataRole.UserRole, pr)
                self.table.setItem(row, col, item)

    def _refresh(self) -> None:
        if hasattr(self._app, "sync_service") and self._app.sync_service:
            self.lbl_status.setText("Syncing…")
            self._app.sync_service.sync("github", force=True)
            self._app.sync_service.sync("bitbucket", force=True)
        else:
            self.reload_from_cache()

    def _open_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        item = self.table.item(rows[0].row(), 0)
        if not item:
            return
        pr = item.data(Qt.ItemDataRole.UserRole) or {}
        url = pr.get("html_url")
        if url:
            QDesktopServices.openUrl(QUrl(url))
