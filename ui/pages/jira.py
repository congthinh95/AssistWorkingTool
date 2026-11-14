"""Jira tasks page."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices, QColor
from PySide6.QtCore import QUrl
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


class JiraPage(QWidget):
    def __init__(self, app: "DevDeskApplication", parent=None) -> None:
        super().__init__(parent)
        self._app = app
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Jira Tasks")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        header.addWidget(title)
        header.addStretch()

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._refresh)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        self.lbl_status = QLabel("Configure Jira in Settings to load issues.")
        self.lbl_status.setObjectName("cardSubtitle")
        layout.addWidget(self.lbl_status)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Key", "Summary", "Status", "Priority", "Project", "Due", "Updated"]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._open_selected)
        layout.addWidget(self.table, stretch=1)

        self.reload_from_cache()

    def reload_from_cache(self) -> None:
        cache = self._app.storage.load_cache("jira")
        data = cache.get("data") or {}
        issues = data.get("issues") or []
        self._populate(issues)
        updated = data.get("updated_at") or cache.get("updated_at")
        if issues:
            overdue = data.get("overdue_count", 0)
            self.lbl_status.setText(
                f"{len(issues)} issue(s) · {overdue} overdue"
                + (f" · last sync {updated}" if updated else "")
            )
        elif data.get("error"):
            self.lbl_status.setText(str(data["error"]))
        else:
            enabled = self._app.config.get("jira.enabled", False)
            self.lbl_status.setText(
                "Jira enabled – waiting for first sync…" if enabled else "Jira not configured. Open Settings."
            )

    def _populate(self, issues: list[dict[str, Any]]) -> None:
        self.table.setRowCount(0)
        for issue in issues:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                issue.get("key", ""),
                issue.get("summary", ""),
                issue.get("status", ""),
                issue.get("priority", ""),
                issue.get("project", ""),
                issue.get("due_date") or "",
                (issue.get("updated") or "")[:19].replace("T", " "),
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if issue.get("overdue") and col in (0, 5):
                    item.setForeground(QColor("#d13438"))
                elif issue.get("stale") and col == 0:
                    item.setForeground(QColor("#ca5010"))
                item.setData(Qt.ItemDataRole.UserRole, issue)
                self.table.setItem(row, col, item)

    def _refresh(self) -> None:
        if hasattr(self._app, "sync_service") and self._app.sync_service:
            self.lbl_status.setText("Syncing…")
            self._app.sync_service.sync("jira", force=True)
        else:
            self.reload_from_cache()

    def _open_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        item = self.table.item(rows[0].row(), 0)
        if not item:
            return
        issue = item.data(Qt.ItemDataRole.UserRole) or {}
        url = issue.get("url")
        if url:
            QDesktopServices.openUrl(QUrl(url))
