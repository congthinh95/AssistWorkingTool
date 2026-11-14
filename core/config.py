"""Application configuration facade over Storage."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

from .logger import get_logger
from .storage import Storage

logger = get_logger("config")


class Config:
    """Typed access to application configuration.

    Changes are kept in memory and persisted via save().
    """

    def __init__(self, storage: Optional[Storage] = None) -> None:
        self._storage = storage or Storage()
        self._data: dict[str, Any] = self._storage.load_config()

    def reload(self) -> None:
        self._data = self._storage.load_config()

    def save(self) -> None:
        self._storage.save_config(self._data)

    @property
    def raw(self) -> dict[str, Any]:
        return self._data

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------

    @property
    def start_with_os(self) -> bool:
        return bool(self._data.get("general", {}).get("start_with_os", False))

    @start_with_os.setter
    def start_with_os(self, value: bool) -> None:
        self._data.setdefault("general", {})["start_with_os"] = bool(value)

    @property
    def start_minimized(self) -> bool:
        return bool(self._data.get("general", {}).get("start_minimized", True))

    @start_minimized.setter
    def start_minimized(self, value: bool) -> None:
        self._data.setdefault("general", {})["start_minimized"] = bool(value)

    @property
    def minimize_on_close(self) -> bool:
        return bool(self._data.get("general", {}).get("minimize_on_close", True))

    @minimize_on_close.setter
    def minimize_on_close(self, value: bool) -> None:
        self._data.setdefault("general", {})["minimize_on_close"] = bool(value)

    @property
    def theme(self) -> str:
        return str(self._data.get("general", {}).get("theme", "system"))

    @theme.setter
    def theme(self, value: str) -> None:
        if value not in ("system", "light", "dark"):
            value = "system"
        self._data.setdefault("general", {})["theme"] = value

    # ------------------------------------------------------------------
    # Integrations (simple getters for Phase 1)
    # ------------------------------------------------------------------

    def get_section(self, name: str) -> dict[str, Any]:
        return deepcopy(self._data.get(name, {}))

    def set_section(self, name: str, value: dict[str, Any]) -> None:
        self._data[name] = value

    def get(self, path: str, default: Any = None) -> Any:
        """Dotted-path getter, e.g. 'jira.enabled'."""
        parts = path.split(".")
        node: Any = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, path: str, value: Any) -> None:
        """Dotted-path setter."""
        parts = path.split(".")
        node = self._data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value
