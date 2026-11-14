"""Local + native OS notifications with click-to-open URL support."""

from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QSystemTrayIcon

from core.logger import get_logger
from core.platform import Platform
from core.storage import Storage

logger = get_logger("notifications")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class NotificationItem:
    id: str
    title: str
    message: str
    category: str
    source_id: str = ""
    url: str = ""
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())
    read: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "category": self.category,
            "source_id": self.source_id,
            "url": self.url,
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
            url=data.get("url", ""),
            created_at=data.get("created_at") or _utcnow().isoformat(),
            read=bool(data.get("read", False)),
        )


class NotificationService(QObject):
    """History, dedup, quiet hours, native toast, click-to-open."""

    MAX_HISTORY = 200
    notification_clicked = Signal(str)  # url

    def __init__(
        self,
        storage: Optional[Storage] = None,
        tray: Optional[QSystemTrayIcon] = None,
        config: Optional[dict] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.storage = storage or Storage()
        self.tray = tray
        self._config = config or {}
        self._history: list[NotificationItem] = []
        self._seen_ids: set[str] = set()
        self._pending_url: str = ""
        self._load()
        if self.tray is not None:
            self._bind_tray(self.tray)

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
        self._bind_tray(tray)

    def _bind_tray(self, tray: QSystemTrayIcon) -> None:
        try:
            tray.messageClicked.connect(self._on_message_clicked)
        except Exception as exc:
            logger.debug("messageClicked bind failed: %s", exc)

    def _on_message_clicked(self) -> None:
        url = self._pending_url
        if url:
            self.open_url(url)
            self.notification_clicked.emit(url)

    @staticmethod
    def open_url(url: str) -> bool:
        if not url:
            return False
        return QDesktopServices.openUrl(QUrl(url))

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
            return now >= t_start or now <= t_end
        except Exception:
            return False

    def _type_enabled(self, category: str) -> bool:
        notif = self._config.get("notifications", {})
        if not notif.get("enabled", True):
            return False
        types = notif.get("types", {})
        return bool(types.get(category, True))

    def _show_native(self, title: str, message: str, url: str = "") -> None:
        notif = self._config.get("notifications", {})
        use_native = bool(notif.get("native_toast", True))

        # Always keep last URL for tray click
        self._pending_url = url or ""

        if self.tray and self.tray.supportsMessages():
            try:
                self.tray.showMessage(
                    title,
                    message if not url else f"{message}\n(Click to open)",
                    QSystemTrayIcon.MessageIcon.Information,
                    8000,
                )
            except Exception as exc:
                logger.debug("Tray showMessage failed: %s", exc)

        if not use_native:
            return

        try:
            if Platform.is_windows():
                self._windows_toast(title, message, url)
            elif Platform.is_linux():
                self._linux_notify(title, message, url)
        except Exception as exc:
            logger.debug("Native toast failed: %s", exc)

    def _windows_toast(self, title: str, message: str, url: str = "") -> None:
        """Best-effort Windows 10/11 toast via PowerShell (no extra pip deps)."""
        # Escape for PowerShell single-quoted strings
        def esc(s: str) -> str:
            return s.replace("'", "''")

        # AppUserModelId style toast via Windows.UI.Notifications is complex;
        # use a simple balloon-compatible toast script.
        ps = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$template = @"
<toast{(' activationType="protocol" launch="' + esc(url) + '"') if url else ''}>
  <visual>
    <binding template="ToastGeneric">
      <text>{esc(title)}</text>
      <text>{esc(message)}</text>
    </binding>
  </visual>
</toast>
"@
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("DevDesk").Show($toast)
"""
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as exc:
            logger.debug("PowerShell toast failed: %s", exc)
            Platform.show_notification(title, message)

    def _linux_notify(self, title: str, message: str, url: str = "") -> None:
        import shutil

        if not shutil.which("notify-send"):
            return
        cmd = [
            "notify-send",
            "--app-name=DevDesk",
            "--urgency=normal",
            title,
            message if not url else f"{message}\n{url}",
        ]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def notify(
        self,
        title: str,
        message: str,
        category: str = "system",
        source_id: str = "",
        url: str = "",
        force: bool = False,
    ) -> Optional[NotificationItem]:
        if source_id and source_id in self._seen_ids and not force:
            return None
        if not force and not self._type_enabled(category):
            return None

        item = NotificationItem(
            id=str(uuid.uuid4()),
            title=title,
            message=message,
            category=category,
            source_id=source_id,
            url=url,
        )
        self._history.append(item)
        if source_id:
            self._seen_ids.add(source_id)
        self._save()

        if force or not self._in_quiet_hours():
            self._show_native(title, message, url)
        else:
            logger.debug("Suppressed toast during quiet hours: %s", title)

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
