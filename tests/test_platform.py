"""Tests for platform abstraction."""

from __future__ import annotations

from pathlib import Path

from core.platform import Platform


def test_platform_name() -> None:
    name = Platform.get_platform_name()
    assert name in ("windows", "linux", "other")


def test_config_directory() -> None:
    path = Platform.get_config_directory()
    assert isinstance(path, Path)
    # Should be under home or APPDATA
    assert path.name.lower() in ("devdesk",)


def test_is_linux_or_windows() -> None:
    # At least one should be true on supported platforms
    assert Platform.is_linux() or Platform.is_windows() or Platform.get_platform_name() == "other"
