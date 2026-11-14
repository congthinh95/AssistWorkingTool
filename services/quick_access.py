"""Quick Access shortcut manager – local only."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from core.logger import get_logger
from core.platform import Platform
from core.storage import Storage

logger = get_logger("quick_access")

SHORTCUT_TYPES = ("folder", "file", "project", "repository", "network", "application", "website")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Shortcut:
    id: str
    name: str
    path: str
    type: str = "folder"
    category: str = "Projects"
    icon: str = ""
    favorite: bool = False
    last_used: Optional[str] = None
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "type": self.type,
            "category": self.category,
            "icon": self.icon,
            "favorite": self.favorite,
            "last_used": self.last_used,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Shortcut":
        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            name=data.get("name", "Unnamed"),
            path=data.get("path", ""),
            type=data.get("type", "folder"),
            category=data.get("category", "Projects"),
            icon=data.get("icon", ""),
            favorite=bool(data.get("favorite", False)),
            last_used=data.get("last_used"),
            created_at=data.get("created_at") or _utcnow().isoformat(),
        )

    def exists(self) -> bool:
        if self.type == "website":
            return bool(urlparse(self.path).scheme)
        if self.type == "application":
            return Path(self.path).exists() or bool(Path(self.path).name)
        return Path(self.path).exists()


class QuickAccessService:
    def __init__(self, storage: Optional[Storage] = None) -> None:
        self.storage = storage or Storage()
        self._shortcuts: list[Shortcut] = []
        self._categories: list[str] = []
        self._favorites: list[str] = []
        self._recent: list[str] = []
        self._load()

    def _load(self) -> None:
        raw = self.storage.load_quick_access()
        self._shortcuts = [Shortcut.from_dict(s) for s in raw.get("shortcuts", [])]
        self._categories = list(raw.get("categories") or [
            "Projects", "Source Code", "Documentation", "Office", "DevOps", "Tools", "Personal"
        ])
        self._favorites = list(raw.get("favorites", []))
        self._recent = list(raw.get("recent", []))

    def _save(self) -> None:
        data = {
            "version": 1,
            "shortcuts": [s.to_dict() for s in self._shortcuts],
            "categories": self._categories,
            "favorites": self._favorites,
            "recent": self._recent,
        }
        self.storage.save_quick_access(data)

    @property
    def shortcuts(self) -> list[Shortcut]:
        return list(self._shortcuts)

    @property
    def categories(self) -> list[str]:
        return list(self._categories)

    def add(
        self,
        name: str,
        path: str,
        type: str = "folder",
        category: str = "Projects",
        favorite: bool = False,
    ) -> Shortcut:
        if type not in SHORTCUT_TYPES:
            type = "folder"
        sc = Shortcut(
            id=str(uuid.uuid4()),
            name=name.strip() or Path(path).name or "Unnamed",
            path=path.strip(),
            type=type,
            category=category,
            favorite=favorite,
        )
        self._shortcuts.append(sc)
        if favorite and sc.id not in self._favorites:
            self._favorites.append(sc.id)
        self._save()
        return sc

    def update(self, shortcut_id: str, **kwargs: Any) -> Optional[Shortcut]:
        for sc in self._shortcuts:
            if sc.id == shortcut_id:
                for key, value in kwargs.items():
                    if hasattr(sc, key) and key != "id":
                        setattr(sc, key, value)
                self._save()
                return sc
        return None

    def delete(self, shortcut_id: str) -> bool:
        before = len(self._shortcuts)
        self._shortcuts = [s for s in self._shortcuts if s.id != shortcut_id]
        self._favorites = [f for f in self._favorites if f != shortcut_id]
        self._recent = [r for r in self._recent if r != shortcut_id]
        if len(self._shortcuts) < before:
            self._save()
            return True
        return False

    def toggle_favorite(self, shortcut_id: str) -> bool:
        for sc in self._shortcuts:
            if sc.id == shortcut_id:
                sc.favorite = not sc.favorite
                if sc.favorite and sc.id not in self._favorites:
                    self._favorites.append(sc.id)
                elif not sc.favorite and sc.id in self._favorites:
                    self._favorites.remove(sc.id)
                self._save()
                return sc.favorite
        return False

    def search(self, query: str) -> list[Shortcut]:
        q = query.lower().strip()
        if not q:
            return self.shortcuts
        return [
            s
            for s in self._shortcuts
            if q in s.name.lower() or q in s.path.lower() or q in s.category.lower()
        ]

    def open(self, shortcut_id: str) -> bool:
        sc = next((s for s in self._shortcuts if s.id == shortcut_id), None)
        if sc is None:
            return False
        ok = False
        if sc.type == "website":
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl

            ok = QDesktopServices.openUrl(QUrl(sc.path))
        elif sc.type in ("folder", "project", "repository", "network"):
            ok = Platform.open_folder(sc.path)
        elif sc.type == "file":
            ok = Platform.open_file(sc.path)
        elif sc.type == "application":
            ok = Platform.launch_application(sc.path)
        else:
            # Fallback
            p = Path(sc.path)
            if p.is_dir():
                ok = Platform.open_folder(p)
            else:
                ok = Platform.open_file(p)

        if ok:
            sc.last_used = _utcnow().isoformat()
            if sc.id in self._recent:
                self._recent.remove(sc.id)
            self._recent.insert(0, sc.id)
            self._recent = self._recent[:20]
            self._save()
        return ok

    def by_category(self, category: str) -> list[Shortcut]:
        return [s for s in self._shortcuts if s.category == category]

    def favorites(self) -> list[Shortcut]:
        id_set = set(self._favorites)
        return [s for s in self._shortcuts if s.id in id_set or s.favorite]
