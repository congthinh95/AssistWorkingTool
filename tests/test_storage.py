"""Tests for JSON storage layer."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.storage import Storage, StorageError


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Storage:
    return Storage(base_dir=tmp_path)


def test_load_config_defaults(tmp_storage: Storage) -> None:
    data = tmp_storage.load_config()
    assert data["version"] == 1
    assert "general" in data
    assert data["general"]["start_minimized"] is True


def test_save_and_reload_config(tmp_storage: Storage) -> None:
    data = tmp_storage.load_config()
    data["general"]["theme"] = "dark"
    tmp_storage.save_config(data)

    reloaded = tmp_storage.load_config()
    assert reloaded["general"]["theme"] == "dark"


def test_atomic_write_creates_backup(tmp_storage: Storage) -> None:
    data = tmp_storage.load_config()
    tmp_storage.save_config(data)
    data["general"]["theme"] = "light"
    tmp_storage.save_config(data)

    bak = tmp_storage.base_dir / "config.json.bak"
    assert bak.exists()


def test_corrupted_json_recovers_from_backup(tmp_storage: Storage) -> None:
    data = tmp_storage.load_config()
    data["general"]["theme"] = "dark"
    tmp_storage.save_config(data)
    # Save again so the .bak contains the known-good "dark" version
    tmp_storage.save_config(data)

    # Corrupt the main file
    path = tmp_storage.base_dir / "config.json"
    path.write_text("{ invalid json", encoding="utf-8")

    recovered = tmp_storage.load_config()
    assert recovered["general"]["theme"] == "dark"


def test_working_time_roundtrip(tmp_storage: Storage) -> None:
    data = tmp_storage.load_working_time()
    data["sessions"].append({"id": "s1", "start": "2026-01-01T09:00:00+00:00"})
    tmp_storage.save_working_time(data)

    reloaded = tmp_storage.load_working_time()
    assert len(reloaded["sessions"]) == 1
    assert reloaded["sessions"][0]["id"] == "s1"


def test_quick_access_defaults(tmp_storage: Storage) -> None:
    data = tmp_storage.load_quick_access()
    assert "Projects" in data["categories"]
    assert data["shortcuts"] == []


def test_cache_roundtrip(tmp_storage: Storage) -> None:
    payload = {"version": 1, "data": [{"key": "TEST-1"}], "updated_at": "2026-01-01"}
    tmp_storage.save_cache("jira", payload)
    loaded = tmp_storage.load_cache("jira")
    assert loaded["data"][0]["key"] == "TEST-1"
