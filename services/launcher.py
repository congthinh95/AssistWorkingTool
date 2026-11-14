"""Developer tools and project launcher service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from core.logger import get_logger
from core.platform import Platform
from core.storage import Storage
from core.config import Config

logger = get_logger("launcher")


@dataclass
class AppShortcut:
    id: str
    name: str
    executable: str
    args: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "executable": self.executable,
            "args": self.args,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppShortcut":
        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            name=data.get("name", ""),
            executable=data.get("executable", ""),
            args=list(data.get("args", [])),
        )


@dataclass
class ProjectShortcut:
    id: str
    name: str
    directory: str
    ide: str = ""
    terminal: str = ""
    repo_url: str = ""
    startup_command: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "directory": self.directory,
            "ide": self.ide,
            "terminal": self.terminal,
            "repo_url": self.repo_url,
            "startup_command": self.startup_command,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectShortcut":
        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            name=data.get("name", ""),
            directory=data.get("directory", ""),
            ide=data.get("ide", ""),
            terminal=data.get("terminal", ""),
            repo_url=data.get("repo_url", ""),
            startup_command=data.get("startup_command", ""),
        )


class LauncherService:
    def __init__(self, config: Optional[Config] = None, storage: Optional[Storage] = None) -> None:
        self.config = config or Config(storage or Storage())
        self._apps: list[AppShortcut] = []
        self._projects: list[ProjectShortcut] = []
        self._load()

    def _load(self) -> None:
        section = self.config.get_section("developer_tools")
        self._apps = [AppShortcut.from_dict(a) for a in section.get("applications", {}).values()] if isinstance(section.get("applications"), dict) else []
        # Also support list form
        apps_raw = section.get("applications")
        if isinstance(apps_raw, list):
            self._apps = [AppShortcut.from_dict(a) for a in apps_raw]
        elif isinstance(apps_raw, dict):
            self._apps = [AppShortcut.from_dict({**v, "id": k, "name": v.get("name", k)}) for k, v in apps_raw.items()]
        self._projects = [ProjectShortcut.from_dict(p) for p in section.get("projects", [])]

    def _save(self) -> None:
        section = self.config.get_section("developer_tools")
        section["applications"] = [a.to_dict() for a in self._apps]
        section["projects"] = [p.to_dict() for p in self._projects]
        self.config.set_section("developer_tools", section)
        self.config.save()

    @property
    def apps(self) -> list[AppShortcut]:
        return list(self._apps)

    @property
    def projects(self) -> list[ProjectShortcut]:
        return list(self._projects)

    def add_app(self, name: str, executable: str, args: Optional[list[str]] = None) -> AppShortcut:
        app = AppShortcut(id=str(uuid.uuid4()), name=name, executable=executable, args=args or [])
        self._apps.append(app)
        self._save()
        return app

    def remove_app(self, app_id: str) -> bool:
        before = len(self._apps)
        self._apps = [a for a in self._apps if a.id != app_id]
        if len(self._apps) < before:
            self._save()
            return True
        return False

    def add_project(
        self,
        name: str,
        directory: str,
        ide: str = "",
        terminal: str = "",
        repo_url: str = "",
    ) -> ProjectShortcut:
        proj = ProjectShortcut(
            id=str(uuid.uuid4()),
            name=name,
            directory=directory,
            ide=ide,
            terminal=terminal,
            repo_url=repo_url,
        )
        self._projects.append(proj)
        self._save()
        return proj

    def remove_project(self, project_id: str) -> bool:
        before = len(self._projects)
        self._projects = [p for p in self._projects if p.id != project_id]
        if len(self._projects) < before:
            self._save()
            return True
        return False

    def launch_app(self, app_id: str) -> bool:
        app = next((a for a in self._apps if a.id == app_id), None)
        if not app:
            return False
        return Platform.launch_application(app.executable, app.args)

    def open_project_folder(self, project_id: str) -> bool:
        proj = next((p for p in self._projects if p.id == project_id), None)
        if not proj:
            return False
        return Platform.open_folder(proj.directory)

    def open_project_ide(self, project_id: str) -> bool:
        proj = next((p for p in self._projects if p.id == project_id), None)
        if not proj or not proj.ide:
            return False
        return Platform.launch_application(proj.ide, [proj.directory])

    def open_project_terminal(self, project_id: str) -> bool:
        proj = next((p for p in self._projects if p.id == project_id), None)
        if not proj:
            return False
        return Platform.open_terminal(proj.directory)

    def open_project_repo(self, project_id: str) -> bool:
        proj = next((p for p in self._projects if p.id == project_id), None)
        if not proj or not proj.repo_url:
            return False
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        return QDesktopServices.openUrl(QUrl(proj.repo_url))
