"""Background synchronization of integrations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot

from core.logger import get_logger
from core.storage import Storage
from core.credential_manager import CredentialManager
from integrations.base import AuthError, IntegrationError
from integrations.jira import JiraClient
from integrations.github import GitHubClient
from integrations.bitbucket import BitbucketClient

if TYPE_CHECKING:
    from core.config import Config
    from services.notifications import NotificationService

logger = get_logger("sync")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SyncSignals(QObject):
    finished = Signal(str, object)  # integration name, result dict or error
    error = Signal(str, str)  # integration name, message
    status = Signal(str)  # human status message


class SyncWorker(QRunnable):
    def __init__(self, name: str, fn, signals: SyncSignals) -> None:
        super().__init__()
        self.name = name
        self.fn = fn
        self.signals = signals
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        try:
            result = self.fn()
            self.signals.finished.emit(self.name, result)
        except Exception as exc:
            logger.exception("Sync %s failed", self.name)
            self.signals.error.emit(self.name, str(exc))
            self.signals.finished.emit(self.name, {"error": str(exc)})


class SyncService(QObject):
    """Coordinates periodic and manual sync of enabled integrations."""

    data_updated = Signal(str)  # integration name
    status_changed = Signal(str)

    def __init__(
        self,
        config: "Config",
        storage: Storage,
        credentials: CredentialManager,
        notifications: Optional["NotificationService"] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.storage = storage
        self.credentials = credentials
        self.notifications = notifications
        self.pool = QThreadPool.globalInstance()
        self._busy: set[str] = set()
        self._last_sync: dict[str, str] = {}
        self._signals = SyncSignals()
        self._signals.finished.connect(self._on_finished)
        self._signals.error.connect(self._on_error)

        self._timers: dict[str, QTimer] = {}
        self._setup_timers()

    def _setup_timers(self) -> None:
        intervals = {
            "jira": int(self.config.get("jira.sync_interval_minutes", 5)) * 60 * 1000,
            "github": int(self.config.get("github.sync_interval_minutes", 3)) * 60 * 1000,
            "bitbucket": int(self.config.get("bitbucket.sync_interval_minutes", 3)) * 60 * 1000,
        }
        for name, ms in intervals.items():
            timer = QTimer(self)
            timer.setInterval(max(ms, 60_000))
            timer.timeout.connect(lambda n=name: self.sync(n))
            self._timers[name] = timer

    def start(self) -> None:
        for name, timer in self._timers.items():
            if self._is_enabled(name):
                timer.start()
                # Initial sync shortly after start
                QTimer.singleShot(2000, lambda n=name: self.sync(n))
        logger.info("Sync timers started")

    def stop(self) -> None:
        for timer in self._timers.values():
            timer.stop()
        self.pool.waitForDone(3000)
        logger.info("Sync stopped")

    def _is_enabled(self, name: str) -> bool:
        return bool(self.config.get(f"{name}.enabled", False))

    def refresh_intervals(self) -> None:
        self._setup_timers()
        for name, timer in self._timers.items():
            if self._is_enabled(name) and not timer.isActive():
                timer.start()
            elif not self._is_enabled(name) and timer.isActive():
                timer.stop()

    def sync(self, name: str, force: bool = False) -> None:
        if name in self._busy and not force:
            logger.debug("Sync %s already running", name)
            return
        if not self._is_enabled(name) and not force:
            return
        self._busy.add(name)
        self.status_changed.emit(f"Syncing {name}…")
        worker = SyncWorker(name, lambda: self._do_sync(name), self._signals)
        self.pool.start(worker)

    def sync_all(self) -> None:
        for name in ("jira", "github", "bitbucket"):
            if self._is_enabled(name):
                self.sync(name)

    def _do_sync(self, name: str) -> dict[str, Any]:
        if name == "jira":
            return self._sync_jira()
        if name == "github":
            return self._sync_github()
        if name == "bitbucket":
            return self._sync_bitbucket()
        return {"error": f"Unknown integration: {name}"}

    def _sync_jira(self) -> dict[str, Any]:
        base_url = self.config.get("jira.base_url", "")
        email = self.config.get("jira.email", "")
        token = self.credentials.get_jira_token()
        if not base_url or not email or not token:
            return {"error": "Jira not configured", "configured": False}

        client = JiraClient(base_url, email, token)
        try:
            jql = self.config.get(
                "jira.jql",
                "assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC",
            )
            issues_raw = client.get_my_issues(jql)
            issues = []
            overdue = 0
            for raw in issues_raw:
                norm = JiraClient.normalize_issue(raw)
                norm["url"] = f"{base_url.rstrip('/')}/browse/{norm['key']}"
                if JiraClient.is_overdue(norm):
                    overdue += 1
                    norm["overdue"] = True
                else:
                    norm["overdue"] = False
                norm["stale"] = JiraClient.is_stale(norm, 7)
                issues.append(norm)

            payload = {
                "issues": issues,
                "count": len(issues),
                "overdue_count": overdue,
                "updated_at": _utcnow_iso(),
            }
            self.storage.save_cache("jira", {"version": 1, "data": payload, "updated_at": _utcnow_iso()})

            # Notifications for new assignments / overdue
            if self.notifications:
                for issue in issues:
                    if issue.get("overdue"):
                        self.notifications.notify(
                            "Jira overdue",
                            f"{issue['key']}: {issue['summary']}",
                            category="jira_overdue",
                            source_id=f"overdue:{issue['key']}",
                        )
            return payload
        finally:
            client.close()

    def _sync_github(self) -> dict[str, Any]:
        accounts = self.config.get("github.accounts", []) or []
        # Support single-token mode via first account or default key
        token = None
        if accounts and isinstance(accounts, list) and accounts:
            acc = accounts[0]
            name = acc.get("name") or acc.get("login") or "default"
            token = self.credentials.get_github_token(name)
        if not token:
            token = self.credentials.get("github_pat_default") or self.credentials.get_github_token("default")
        if not token:
            return {"error": "GitHub not configured", "configured": False}

        client = GitHubClient(token)
        try:
            review_raw = client.get_notifications_prs()
            mine_raw = client.get_my_open_prs()
            review = [GitHubClient.normalize_pr(p) for p in review_raw]
            mine = [GitHubClient.normalize_pr(p) for p in mine_raw]
            payload = {
                "pull_requests": review + mine,
                "review_count": len(review),
                "my_count": len(mine),
                "updated_at": _utcnow_iso(),
            }
            self.storage.save_cache("github", {"version": 1, "data": payload, "updated_at": _utcnow_iso()})

            if self.notifications:
                for pr in review:
                    self.notifications.notify(
                        "PR review requested",
                        f"#{pr['number']}: {pr['title']}",
                        category="pr_review",
                        source_id=f"gh-review:{pr.get('html_url') or pr['number']}",
                    )
            return payload
        finally:
            client.close()

    def _sync_bitbucket(self) -> dict[str, Any]:
        workspaces = self.config.get("bitbucket.workspaces", []) or []
        token = self.credentials.get_bitbucket_token()
        username = self.config.get("bitbucket.username", "")
        if not token or not username:
            return {"error": "Bitbucket not configured", "configured": False}

        client = BitbucketClient(username, token)
        try:
            all_prs: list[dict] = []
            review_count = 0
            for ws in workspaces:
                ws_name = ws if isinstance(ws, str) else ws.get("slug") or ws.get("name", "")
                if not ws_name:
                    continue
                raw_prs = client.get_prs_to_review(ws_name)
                for raw in raw_prs:
                    norm = BitbucketClient.normalize_pr(raw)
                    all_prs.append(norm)
                    review_count += 1
            payload = {
                "pull_requests": all_prs,
                "review_count": review_count,
                "my_count": 0,
                "updated_at": _utcnow_iso(),
            }
            self.storage.save_cache("bitbucket", {"version": 1, "data": payload, "updated_at": _utcnow_iso()})
            return payload
        finally:
            client.close()

    @Slot(str, object)
    def _on_finished(self, name: str, result: object) -> None:
        self._busy.discard(name)
        self._last_sync[name] = _utcnow_iso()
        if isinstance(result, dict) and result.get("error"):
            self.status_changed.emit(f"{name}: {result['error']}")
        else:
            self.status_changed.emit(f"{name} synced")
            self.data_updated.emit(name)

    @Slot(str, str)
    def _on_error(self, name: str, message: str) -> None:
        logger.error("Sync error [%s]: %s", name, message)
        self.status_changed.emit(f"{name} error: {message}")

    def last_sync(self, name: str) -> Optional[str]:
        return self._last_sync.get(name)

    def get_cached(self, name: str) -> dict[str, Any]:
        return self.storage.load_cache(name)
