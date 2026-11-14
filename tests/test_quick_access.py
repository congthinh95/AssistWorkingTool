"""Tests for Quick Access service."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.storage import Storage
from services.quick_access import QuickAccessService


@pytest.fixture
def service(tmp_path: Path) -> QuickAccessService:
    return QuickAccessService(storage=Storage(base_dir=tmp_path))


def test_add_and_list(service: QuickAccessService, tmp_path: Path) -> None:
    folder = tmp_path / "proj"
    folder.mkdir()
    sc = service.add("My Project", str(folder), type="project", category="Projects")
    assert sc.name == "My Project"
    assert len(service.shortcuts) == 1
    assert service.shortcuts[0].exists()


def test_delete(service: QuickAccessService, tmp_path: Path) -> None:
    sc = service.add("Temp", str(tmp_path), type="folder")
    assert service.delete(sc.id)
    assert len(service.shortcuts) == 0


def test_search(service: QuickAccessService, tmp_path: Path) -> None:
    service.add("Alpha", str(tmp_path), category="Projects")
    service.add("Beta Docs", str(tmp_path), category="Documentation")
    results = service.search("doc")
    assert len(results) == 1
    assert results[0].name == "Beta Docs"


def test_favorite(service: QuickAccessService, tmp_path: Path) -> None:
    sc = service.add("Fav", str(tmp_path))
    assert not sc.favorite
    service.toggle_favorite(sc.id)
    assert service.shortcuts[0].favorite
    assert len(service.favorites()) == 1


def test_persistence(tmp_path: Path) -> None:
    s1 = QuickAccessService(storage=Storage(base_dir=tmp_path))
    s1.add("Persist", str(tmp_path))
    s2 = QuickAccessService(storage=Storage(base_dir=tmp_path))
    assert len(s2.shortcuts) == 1
    assert s2.shortcuts[0].name == "Persist"
