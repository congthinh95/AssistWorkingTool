"""Tests for Working Time service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.storage import Storage
from services.working_time import WorkingTimeService, WorkSession


@pytest.fixture
def service(tmp_path: Path) -> WorkingTimeService:
    storage = Storage(base_dir=tmp_path)
    return WorkingTimeService(storage=storage, daily_target_hours=8.0)


def test_check_in_out(service: WorkingTimeService) -> None:
    assert service.status == "idle"
    session = service.check_in()
    assert service.status == "working"
    assert session.is_active
    assert service.current_session is not None

    service.check_out()
    assert service.status == "idle"
    assert service.current_session is None
    assert not session.is_active


def test_double_check_in_raises(service: WorkingTimeService) -> None:
    service.check_in()
    with pytest.raises(ValueError, match="Already checked in"):
        service.check_in()


def test_break_cycle(service: WorkingTimeService) -> None:
    service.check_in()
    service.start_break()
    assert service.status == "break"
    service.end_break()
    assert service.status == "working"
    service.check_out()
    assert service.status == "idle"


def test_persistence(tmp_path: Path) -> None:
    storage = Storage(base_dir=tmp_path)
    s1 = WorkingTimeService(storage=storage)
    s1.check_in()
    sid = s1.current_session.id

    s2 = WorkingTimeService(storage=storage)
    assert s2.status == "working"
    assert s2.current_session is not None
    assert s2.current_session.id == sid


def test_summary_format(service: WorkingTimeService) -> None:
    summary = service.summary_today()
    assert "worked" in summary
    assert summary["status"] == "idle"
    line = service.format_status_line()
    assert "Not checked in" in line


def test_invalid_checkout(service: WorkingTimeService) -> None:
    with pytest.raises(ValueError, match="Not currently checked in"):
        service.check_out()
