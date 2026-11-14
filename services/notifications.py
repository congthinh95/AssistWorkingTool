"""Local notification service – history, deduplication, quiet hours."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import Any, Optional

from PySide6.QtWidgets import QSystemTrayIcon

from core.logger import get_logger
from core.storage import Storage

logger = get_logger("notifications")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class NotificationItem:
    id: str
    title: str
    message: str
    category: str  # jira_assignment, jira_overdue, pr_review, pr_ci_failure, working_time, system
    source_id: str = ""  # issue key / PR url for dedup
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())
    read: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "category": self.category,
            "source_id": self.source_id,
            "created_at": self.created_at,
            "read": self.read,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NotificationItem":
        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            title=data.get("title", ""),
            message=data.get("message", ""),
            category=data.get("category", "system"),
            source_id=data.get("source_id", ""),
            created_at=data.get("created_at") or _utcnow().isoformat(),
            read=bool(data.get("read", False)),
        )


class NotificationService:
    """Manages notification history and OS notifications via tray."""

    MAX_HISTORY = 200

    def __init__(
        self,
        storage: Optional[Storage] = None,
        tray: Optional[QSystemTrayIcon] = None,
        config: Optional[dict] = None,
    ) -> None:
        self.storage = storage or Storage()
        self.tray = tray
        self._config = config or {}
        self._history: list[NotificationItem] = []
        self._seen_ids: set[str] = set()
        self._load()

    def _load(self) -> None:
        raw = self.storage.load_notifications()
        self._history = [NotificationItem.from_dict(n) for n in raw.get("history", [])]
        self._seen_ids = set(raw.get("seen_ids", []))

    def _save(self) -> None:
        data = {
            "version": 1,
            "history": [n.to_dict() for n in self._history[-self.MAX_HISTORY :]],
            "seen_ids": list(self._seen_ids)[-500:],
        }
        self.storage.save_notifications(data)

    def update_config(self, config: dict) -> None:
        self._config = config

    def set_tray(self, tray: QSystemTrayIcon) -> None:
        self.tray = tray

    def _in_quiet_hours(self) -> bool:
        notif = self._config.get("notifications", {})
        start = notif.get("quiet_hours_start")
        end = notif.get("quiet_hours_end")
        if not start or not end:
            return False
        try:
            h1, m1 = map(int, str(start).split(":"))
            h2, m2 = map(int, str(end).split(":"))
            now = datetime.now().time()
            t_start = time(h1, m1)
            t_end = time(h2, m2)
            if t_start <= t_end:
                return t_start <= now <= t_end
            # Overnight quiet hours
            return now >= t_start or now <= t_end
        except Exception:
            return False

    def _type_enabled(self, category: str) -> bool:
        notif = self._config.get("notifications", {})
        if not notif.get("enabled", True):
            return False
        types = notif.get("types", {})
        return bool(types.get(category, True))

    def notify(
        self,
        title: str,
        message: str,
        category: str = "system",
        source_id: str = "",
        force: bool = False,
    ) -> Optional[NotificationItem]:
        """Show notification and record in history. Deduplicates by source_id."""
        if source_id and source_id in self._seen_ids and not force:
            return None
        if not force and not self._type_enabled(category):
            return None
        if not force and self._in_quiet_hours():
            logger.debug("Suppressed notification during quiet hours: %s", title)
            # Still record in history
            item = NotificationItem(
                id=str(uuid.uuid4()),
                title=title,
                message=message,
                category=category,
                source_id=source_id,
            )
            self._history.append(item)
            if source_id:
                self._seen_ids.add(source_id)
            self._save()
            return item

        item = NotificationItem(
            id=str(uuid.uuid4()),
            title=title,
            message=message,
            category=category,
            source_id=source_id,
        )
        self._history.append(item)
        if source_id:
            self._seen_ids.add(source_id)
        self._save()

        if self.tray and self.tray.supportsMessages():
            try:
                self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 5000)
            except Exception as exc:
                logger.debug("Tray notification failed: %s", exc)

        logger.info("Notification [%s]: %s – %s", category, title, message)
        return item

    @property
    def history(self) -> list[NotificationItem]:
        return list(reversed(self._history))

    def mark_read(self, notif_id: str) -> None:
        for n in self._history:
            if n.id == notif_id:
                n.read = True
                self._save()
                return

    def clear_history(self) -> None:
        self._history.clear()
        self._save()
