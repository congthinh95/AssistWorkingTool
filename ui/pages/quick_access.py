"""Quick Access page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.quick_access import QuickAccessService, SHORTCUT_TYPES

if TYPE_CHECKING:
    from core.application import DevDeskApplication


class AddShortcutDialog(QDialog):
    def __init__(self, categories: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Shortcut")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)

        self.name = QLineEdit()
        layout.addRow("Name", self.name)

        self.path = QLineEdit()
        layout.addRow("Path / URL", self.path)

        self.type = QComboBox()
        self.type.addItems(list(SHORTCUT_TYPES))
        layout.addRow("Type", self.type)

        self.category = QComboBox()
        self.category.addItems(categories)
        self.category.setEditable(True)
        layout.addRow("Category", self.category)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> tuple[str, str, str, str]:
        return (
            self.name.text().strip(),
            self.path.text().strip(),
            self.type.currentText(),
            self.category.currentText().strip() or "Projects",
        )


class QuickAccessPage(QWidget):
    def __init__(self, app: "DevDeskApplication", parent=None) -> None:
        super().__init__(parent)
        self._app = app
        self.service = QuickAccessService(storage=app.storage)
        self._build()
        self._reload_list()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel("Quick Access")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        # Search + actions
        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search shortcuts…")
        self.search.textChanged.connect(self._on_search)
        row.addWidget(self.search, stretch=1)

        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self._on_add)
        row.addWidget(self.btn_add)

        self.btn_open = QPushButton("Open")
        self.btn_open.setObjectName("secondary")
        self.btn_open.clicked.connect(self._on_open)
        row.addWidget(self.btn_open)

        self.btn_fav = QPushButton("★")
        self.btn_fav.setObjectName("secondary")
        self.btn_fav.setFixedWidth(40)
        self.btn_fav.clicked.connect(self._on_favorite)
        row.addWidget(self.btn_fav)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("secondary")
        self.btn_delete.clicked.connect(self._on_delete)
        row.addWidget(self.btn_delete)

        layout.addLayout(row)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _: self._on_open())
        layout.addWidget(self.list, stretch=1)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("cardSubtitle")
        layout.addWidget(self.lbl_status)

    def _reload_list(self, items=None) -> None:
        self.list.clear()
        shortcuts = items if items is not None else self.service.shortcuts
        for sc in shortcuts:
            star = "★ " if sc.favorite else ""
            missing = "" if sc.exists() or sc.type == "website" else "  [missing]"
            text = f"{star}{sc.name}  ·  {sc.type}  ·  {sc.category}{missing}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, sc.id)
            item.setToolTip(sc.path)
            self.list.addItem(item)
        self.lbl_status.setText(f"{len(shortcuts)} shortcut(s)")

    def _selected_id(self) -> str | None:
        item = self.list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_search(self, text: str) -> None:
        self._reload_list(self.service.search(text))

    def _on_add(self) -> None:
        dlg = AddShortcutDialog(self.service.categories, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name, path, typ, category = dlg.values()
        if not path:
            QMessageBox.warning(self, "Quick Access", "Path or URL is required.")
            return
        self.service.add(name=name, path=path, type=typ, category=category)
        self._reload_list()

    def _on_open(self) -> None:
        sid = self._selected_id()
        if not sid:
            return
        if not self.service.open(sid):
            QMessageBox.warning(
                self,
                "Quick Access",
                "Could not open the shortcut. Path may no longer exist.",
            )

    def _on_favorite(self) -> None:
        sid = self._selected_id()
        if not sid:
            return
        self.service.toggle_favorite(sid)
        self._reload_list()

    def _on_delete(self) -> None:
        sid = self._selected_id()
        if not sid:
            return
        reply = QMessageBox.question(
            self,
            "Quick Access",
            "Delete this shortcut?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.service.delete(sid)
            self._reload_list()
