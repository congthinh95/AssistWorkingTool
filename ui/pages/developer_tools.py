"""Developer Tools launcher page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.platform import Platform
from services.launcher import LauncherService

if TYPE_CHECKING:
    from core.application import DevDeskApplication


class AddAppDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Application")
        form = QFormLayout(self)
        self.name = QLineEdit()
        form.addRow("Name", self.name)
        self.exe = QLineEdit()
        form.addRow("Executable", self.exe)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


class AddProjectDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Project")
        form = QFormLayout(self)
        self.name = QLineEdit()
        form.addRow("Name", self.name)
        self.directory = QLineEdit()
        form.addRow("Directory", self.directory)
        self.ide = QLineEdit()
        self.ide.setPlaceholderText("Optional IDE executable")
        form.addRow("IDE", self.ide)
        self.repo = QLineEdit()
        self.repo.setPlaceholderText("Optional repository URL")
        form.addRow("Repo URL", self.repo)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


class DeveloperToolsPage(QWidget):
    def __init__(self, app: "DevDeskApplication", parent=None) -> None:
        super().__init__(parent)
        self._app = app
        self.service = LauncherService(config=app.config, storage=app.storage)
        self._build()
        self._reload()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel("Developer Tools")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        tabs = QTabWidget()

        # Apps tab
        apps_w = QWidget()
        apps_l = QVBoxLayout(apps_w)
        row = QHBoxLayout()
        btn_add_app = QPushButton("Add App")
        btn_add_app.clicked.connect(self._add_app)
        row.addWidget(btn_add_app)
        btn_launch = QPushButton("Launch")
        btn_launch.setObjectName("secondary")
        btn_launch.clicked.connect(self._launch_app)
        row.addWidget(btn_launch)
        btn_rm_app = QPushButton("Remove")
        btn_rm_app.setObjectName("secondary")
        btn_rm_app.clicked.connect(self._remove_app)
        row.addWidget(btn_rm_app)
        row.addStretch()
        apps_l.addLayout(row)
        self.app_list = QListWidget()
        self.app_list.itemDoubleClicked.connect(lambda _: self._launch_app())
        apps_l.addWidget(self.app_list)
        tabs.addTab(apps_w, "Applications")

        # Projects tab
        proj_w = QWidget()
        proj_l = QVBoxLayout(proj_w)
        row2 = QHBoxLayout()
        btn_add_proj = QPushButton("Add Project")
        btn_add_proj.clicked.connect(self._add_project)
        row2.addWidget(btn_add_proj)
        btn_folder = QPushButton("Open Folder")
        btn_folder.setObjectName("secondary")
        btn_folder.clicked.connect(self._open_folder)
        row2.addWidget(btn_folder)
        btn_ide = QPushButton("Open IDE")
        btn_ide.setObjectName("secondary")
        btn_ide.clicked.connect(self._open_ide)
        row2.addWidget(btn_ide)
        btn_term = QPushButton("Terminal")
        btn_term.setObjectName("secondary")
        btn_term.clicked.connect(self._open_terminal)
        row2.addWidget(btn_term)
        btn_repo = QPushButton("Repo")
        btn_repo.setObjectName("secondary")
        btn_repo.clicked.connect(self._open_repo)
        row2.addWidget(btn_repo)
        btn_rm_proj = QPushButton("Remove")
        btn_rm_proj.setObjectName("secondary")
        btn_rm_proj.clicked.connect(self._remove_project)
        row2.addWidget(btn_rm_proj)
        row2.addStretch()
        proj_l.addLayout(row2)
        self.proj_list = QListWidget()
        proj_l.addWidget(self.proj_list)
        tabs.addTab(proj_w, "Projects")

        # Quick actions
        quick_w = QWidget()
        ql = QVBoxLayout(quick_w)
        self.edit_path = QLineEdit()
        self.edit_path.setPlaceholderText("Executable path")
        ql.addWidget(self.edit_path)
        self.edit_cwd = QLineEdit()
        self.edit_cwd.setPlaceholderText("Working directory (optional)")
        ql.addWidget(self.edit_cwd)
        qr = QHBoxLayout()
        b1 = QPushButton("Launch")
        b1.clicked.connect(lambda: Platform.launch_application(self.edit_path.text().strip()) if self.edit_path.text().strip() else None)
        qr.addWidget(b1)
        b2 = QPushButton("Open Terminal")
        b2.setObjectName("secondary")
        b2.clicked.connect(lambda: Platform.open_terminal(self.edit_cwd.text().strip() or None))
        qr.addWidget(b2)
        b3 = QPushButton("Open Folder")
        b3.setObjectName("secondary")
        b3.clicked.connect(lambda: Platform.open_folder(self.edit_cwd.text().strip()) if self.edit_cwd.text().strip() else None)
        qr.addWidget(b3)
        qr.addStretch()
        ql.addLayout(qr)
        ql.addStretch()
        tabs.addTab(quick_w, "Quick")

        layout.addWidget(tabs, stretch=1)

    def _reload(self) -> None:
        self.app_list.clear()
        for app in self.service.apps:
            item = QListWidgetItem(f"{app.name}  ·  {app.executable}")
            item.setData(Qt.ItemDataRole.UserRole, app.id)
            self.app_list.addItem(item)
        self.proj_list.clear()
        for p in self.service.projects:
            item = QListWidgetItem(f"{p.name}  ·  {p.directory}")
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            item.setToolTip(p.directory)
            self.proj_list.addItem(item)

    def _add_app(self) -> None:
        dlg = AddAppDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name, exe = dlg.name.text().strip(), dlg.exe.text().strip()
        if not name or not exe:
            return
        self.service.add_app(name, exe)
        self._reload()

    def _launch_app(self) -> None:
        item = self.app_list.currentItem()
        if not item:
            return
        if not self.service.launch_app(item.data(Qt.ItemDataRole.UserRole)):
            QMessageBox.warning(self, "Developer Tools", "Failed to launch application.")

    def _remove_app(self) -> None:
        item = self.app_list.currentItem()
        if not item:
            return
        self.service.remove_app(item.data(Qt.ItemDataRole.UserRole))
        self._reload()

    def _add_project(self) -> None:
        dlg = AddProjectDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name = dlg.name.text().strip()
        directory = dlg.directory.text().strip()
        if not name or not directory:
            return
        self.service.add_project(name, directory, ide=dlg.ide.text().strip(), repo_url=dlg.repo.text().strip())
        self._reload()

    def _selected_project_id(self) -> str | None:
        item = self.proj_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _open_folder(self) -> None:
        pid = self._selected_project_id()
        if pid:
            self.service.open_project_folder(pid)

    def _open_ide(self) -> None:
        pid = self._selected_project_id()
        if pid and not self.service.open_project_ide(pid):
            QMessageBox.information(self, "Developer Tools", "No IDE configured for this project.")

    def _open_terminal(self) -> None:
        pid = self._selected_project_id()
        if pid:
            self.service.open_project_terminal(pid)

    def _open_repo(self) -> None:
        pid = self._selected_project_id()
        if pid and not self.service.open_project_repo(pid):
            QMessageBox.information(self, "Developer Tools", "No repository URL configured.")

    def _remove_project(self) -> None:
        pid = self._selected_project_id()
        if pid:
            self.service.remove_project(pid)
            self._reload()
