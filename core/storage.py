"""JSON-based local storage with atomic writes and recovery."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

from .logger import get_logger
from .platform import Platform

logger = get_logger("storage")

# Current data schema versions
CONFIG_VERSION = 1
WORKING_TIME_VERSION = 1
QUICK_ACCESS_VERSION = 1
NOTIFICATIONS_VERSION = 1
CACHE_VERSION = 1


class StorageError(Exception):
    """Raised when storage operations fail unrecoverably."""


class Storage:
    """Manages all JSON persistence for DevDesk.

    Credentials are never stored here – use CredentialManager + keyring.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or Platform.get_config_directory()
        self.cache_dir = self.base_dir / "cache"
        self.logs_dir = self.base_dir / "logs"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _path(self, name: str) -> Path:
        return self.base_dir / name

    def _cache_path(self, name: str) -> Path:
        return self.cache_dir / name

    def _atomic_write(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON atomically using a temporary file + rename."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        tmp_path = Path(tmp_name)
        try:
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                f.flush()
                os_fsync = getattr(__import__("os"), "fsync", None)
                if os_fsync:
                    os_fsync(f.fileno())
            # Backup existing file if present
            if path.exists():
                backup = path.with_suffix(path.suffix + ".bak")
                try:
                    shutil.copy2(path, backup)
                except Exception as exc:
                    logger.warning("Could not create backup for %s: %s", path, exc)
            tmp_path.replace(path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    def _load_json(self, path: Path, default: Optional[dict] = None) -> dict[str, Any]:
        """Load JSON, recovering from corruption when possible."""
        if not path.exists():
            return default.copy() if default is not None else {}

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Root JSON value must be an object")
            return data
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            logger.error("Failed to load %s: %s – attempting recovery", path, exc)
            # Try backup
            backup = path.with_suffix(path.suffix + ".bak")
            if backup.exists():
                try:
                    with backup.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        logger.info("Recovered %s from backup", path.name)
                        # Restore the good backup as current
                        shutil.copy2(backup, path)
                        return data
                except Exception as bak_exc:
                    logger.error("Backup also corrupted: %s", bak_exc)
            # Last resort: return default
            if default is not None:
                logger.warning("Returning default data for %s", path.name)
                return default.copy()
            raise StorageError(f"Unrecoverable storage corruption: {path}") from exc

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def load_config(self) -> dict[str, Any]:
        default = {
            "version": CONFIG_VERSION,
            "general": {
                "start_with_os": False,
                "start_minimized": True,
                "minimize_on_close": True,
                "theme": "system",  # system | light | dark
                "language": "en",
            },
            "jira": {
                "enabled": False,
                "base_url": "",
                "email": "",
                "jql": "assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC",
                "sync_interval_minutes": 5,
            },
            "github": {
                "enabled": False,
                "accounts": [],
                "sync_interval_minutes": 3,
            },
            "bitbucket": {
                "enabled": False,
                "workspaces": [],
                "sync_interval_minutes": 3,
            },
            "working_time": {
                "daily_target_hours": 8.0,
                "working_days": [0, 1, 2, 3, 4],  # Mon-Fri
                "reminder_interval_minutes": 60,
            },
            "notifications": {
                "enabled": True,
                "quiet_hours_start": None,
                "quiet_hours_end": None,
                "types": {
                    "jira_assignment": True,
                    "jira_overdue": True,
                    "pr_review": True,
                    "pr_ci_failure": True,
                    "working_time": True,
                },
            },
            "developer_tools": {
                "applications": {},
                "default_terminal": "",
                "projects": [],
            },
            "pr_automation": {
                "enabled": False,
                "dry_run": True,
                "approve": {
                    "enabled": False,
                    "require_checks_pass": True,
                    "skip_draft": True,
                    "skip_own_prs": True,
                    "title_exclude": ["WIP", "DO NOT MERGE", "DRAFT"],
                    "repo_allowlist": [],
                    "repo_blocklist": [],
                    "max_files_changed": 0,
                },
                "remove_reviewer": {
                    "enabled": False,
                    "on_new_commits_after_review": False,
                    "on_draft": True,
                    "on_title_keywords": ["WIP", "DO NOT MERGE"],
                    "repo_allowlist": [],
                    "repo_blocklist": [],
                },
            },
        }
        data = self._load_json(self._path("config.json"), default)
        # Ensure version field exists
        if "version" not in data:
            data["version"] = CONFIG_VERSION
        return data

    def save_config(self, data: dict[str, Any]) -> None:
        data["version"] = CONFIG_VERSION
        self._atomic_write(self._path("config.json"), data)

    # ------------------------------------------------------------------
    # Working Time
    # ------------------------------------------------------------------

    def load_working_time(self) -> dict[str, Any]:
        default = {
            "version": WORKING_TIME_VERSION,
            "sessions": [],
            "current_session": None,
        }
        return self._load_json(self._path("working_time.json"), default)

    def save_working_time(self, data: dict[str, Any]) -> None:
        data["version"] = WORKING_TIME_VERSION
        self._atomic_write(self._path("working_time.json"), data)

    # ------------------------------------------------------------------
    # Quick Access
    # ------------------------------------------------------------------

    def load_quick_access(self) -> dict[str, Any]:
        default = {
            "version": QUICK_ACCESS_VERSION,
            "shortcuts": [],
            "categories": [
                "Projects",
                "Source Code",
                "Documentation",
                "Office",
                "DevOps",
                "Tools",
                "Personal",
            ],
            "favorites": [],
            "recent": [],
        }
        return self._load_json(self._path("quick_access.json"), default)

    def save_quick_access(self, data: dict[str, Any]) -> None:
        data["version"] = QUICK_ACCESS_VERSION
        self._atomic_write(self._path("quick_access.json"), data)

    # ------------------------------------------------------------------
    # Notifications history
    # ------------------------------------------------------------------

    def load_notifications(self) -> dict[str, Any]:
        default = {
            "version": NOTIFICATIONS_VERSION,
            "history": [],
            "seen_ids": [],
        }
        return self._load_json(self._path("notifications.json"), default)

    def save_notifications(self, data: dict[str, Any]) -> None:
        data["version"] = NOTIFICATIONS_VERSION
        self._atomic_write(self._path("notifications.json"), data)

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def load_cache(self, name: str) -> dict[str, Any]:
        default = {"version": CACHE_VERSION, "data": None, "updated_at": None}
        return self._load_json(self._cache_path(f"{name}.json"), default)

    def save_cache(self, name: str, data: dict[str, Any]) -> None:
        data["version"] = CACHE_VERSION
        self._atomic_write(self._cache_path(f"{name}.json"), data)

    def clear_cache(self, name: Optional[str] = None) -> None:
        if name:
            path = self._cache_path(f"{name}.json")
            if path.exists():
                path.unlink()
        else:
            for p in self.cache_dir.glob("*.json"):
                p.unlink()


    # ------------------------------------------------------------------
    # PR automation audit log
    # ------------------------------------------------------------------

    def load_automation_log(self) -> dict[str, Any]:
        default = {"version": 1, "entries": []}
        return self._load_json(self._path("automation_log.json"), default)

    def save_automation_log(self, data: dict[str, Any]) -> None:
        data["version"] = 1
        # Keep last 500 entries
        entries = data.get("entries") or []
        if len(entries) > 500:
            data["entries"] = entries[-500:]
        self._atomic_write(self._path("automation_log.json"), data)

    def append_automation_log(self, entry: dict[str, Any]) -> None:
        data = self.load_automation_log()
        data.setdefault("entries", []).append(entry)
        self.save_automation_log(data)
