"""Local Working Time tracker – fully offline, JSON persistence."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from core.logger import get_logger
from core.storage import Storage

logger = get_logger("working_time")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: str | datetime | None) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    # ISO format
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _fmt_duration(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


@dataclass
class BreakInterval:
    start: datetime
    end: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BreakInterval":
        return cls(
            start=_parse_ts(data["start"]) or _utcnow(),
            end=_parse_ts(data.get("end")),
        )

    @property
    def duration_seconds(self) -> float:
        end = self.end or _utcnow()
        return max(0.0, (end - self.start).total_seconds())


@dataclass
class WorkSession:
    id: str
    start: datetime
    end: Optional[datetime] = None
    breaks: list[BreakInterval] = field(default_factory=list)
    notes: str = ""
    last_modified: datetime = field(default_factory=_utcnow)
    corrections: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end else None,
            "breaks": [b.to_dict() for b in self.breaks],
            "notes": self.notes,
            "last_modified": self.last_modified.isoformat(),
            "corrections": self.corrections,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkSession":
        return cls(
            id=data["id"],
            start=_parse_ts(data["start"]) or _utcnow(),
            end=_parse_ts(data.get("end")),
            breaks=[BreakInterval.from_dict(b) for b in data.get("breaks", [])],
            notes=data.get("notes", ""),
            last_modified=_parse_ts(data.get("last_modified")) or _utcnow(),
            corrections=list(data.get("corrections", [])),
        )

    @property
    def is_active(self) -> bool:
        return self.end is None

    @property
    def is_on_break(self) -> bool:
        if not self.breaks:
            return False
        last = self.breaks[-1]
        return last.end is None

    def working_seconds(self, until: Optional[datetime] = None) -> float:
        """Net working time (excluding breaks)."""
        until = until or (self.end or _utcnow())
        total = (until - self.start).total_seconds()
        break_secs = sum(b.duration_seconds for b in self.breaks)
        # If currently on break, the open break is already counted up to `until`
        return max(0.0, total - break_secs)

    def break_seconds(self, until: Optional[datetime] = None) -> float:
        until = until or (self.end or _utcnow())
        total = 0.0
        for b in self.breaks:
            end = b.end or until
            total += max(0.0, (end - b.start).total_seconds())
        return total


class WorkingTimeService:
    """Manages working sessions and summaries."""

    def __init__(self, storage: Optional[Storage] = None, daily_target_hours: float = 8.0) -> None:
        self.storage = storage or Storage()
        self.daily_target_hours = daily_target_hours
        self._sessions: list[WorkSession] = []
        self._current: Optional[WorkSession] = None
        self._load()

    def _load(self) -> None:
        raw = self.storage.load_working_time()
        self._sessions = [WorkSession.from_dict(s) for s in raw.get("sessions", [])]
        current_id = raw.get("current_session")
        self._current = None
        if current_id:
            for s in self._sessions:
                if s.id == current_id and s.is_active:
                    self._current = s
                    break
        # Also pick up any active session that wasn't marked as current
        if self._current is None:
            for s in reversed(self._sessions):
                if s.is_active:
                    self._current = s
                    break

    def _save(self) -> None:
        data = {
            "version": 1,
            "sessions": [s.to_dict() for s in self._sessions],
            "current_session": self._current.id if self._current else None,
        }
        self.storage.save_working_time(data)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def check_in(self, notes: str = "") -> WorkSession:
        if self._current is not None and self._current.is_active:
            raise ValueError("Already checked in. Check out first.")
        session = WorkSession(
            id=str(uuid.uuid4()),
            start=_utcnow(),
            notes=notes,
        )
        self._sessions.append(session)
        self._current = session
        self._save()
        logger.info("Checked in: %s", session.id)
        return session

    def check_out(self) -> WorkSession:
        if self._current is None or not self._current.is_active:
            raise ValueError("Not currently checked in.")
        if self._current.is_on_break:
            self.end_break()
        self._current.end = _utcnow()
        self._current.last_modified = _utcnow()
        session = self._current
        self._current = None
        self._save()
        logger.info("Checked out: %s", session.id)
        return session

    def start_break(self) -> BreakInterval:
        if self._current is None or not self._current.is_active:
            raise ValueError("Not currently checked in.")
        if self._current.is_on_break:
            raise ValueError("Already on break.")
        br = BreakInterval(start=_utcnow())
        self._current.breaks.append(br)
        self._current.last_modified = _utcnow()
        self._save()
        return br

    def end_break(self) -> BreakInterval:
        if self._current is None or not self._current.is_active:
            raise ValueError("Not currently checked in.")
        if not self._current.is_on_break:
            raise ValueError("Not currently on break.")
        br = self._current.breaks[-1]
        br.end = _utcnow()
        self._current.last_modified = _utcnow()
        self._save()
        return br

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def current_session(self) -> Optional[WorkSession]:
        return self._current

    @property
    def status(self) -> str:
        if self._current is None:
            return "idle"
        if self._current.is_on_break:
            return "break"
        return "working"

    def today_sessions(self) -> list[WorkSession]:
        today = date.today()
        result = []
        for s in self._sessions:
            # Include sessions that started today or are still active and crossed midnight
            start_date = s.start.astimezone().date()
            if start_date == today or (s.is_active and start_date < today):
                result.append(s)
        return result

    def today_working_seconds(self) -> float:
        total = 0.0
        today = date.today()
        for s in self.today_sessions():
            # Clamp to today if session spans midnight
            start = s.start
            end = s.end or _utcnow()
            day_start = datetime.combine(today, datetime.min.time(), tzinfo=start.tzinfo)
            day_end = day_start + timedelta(days=1)
            effective_start = max(start, day_start)
            effective_end = min(end, day_end)
            if effective_end <= effective_start:
                continue
            # Approximate: use full session working ratio
            session_secs = (end - start).total_seconds()
            if session_secs <= 0:
                continue
            portion = (effective_end - effective_start).total_seconds() / session_secs
            total += s.working_seconds() * portion
        return total

    def today_break_seconds(self) -> float:
        return sum(s.break_seconds() for s in self.today_sessions())

    def remaining_seconds(self) -> float:
        target = self.daily_target_hours * 3600
        return max(0.0, target - self.today_working_seconds())

    def summary_today(self) -> dict[str, Any]:
        worked = self.today_working_seconds()
        breaks = self.today_break_seconds()
        target = self.daily_target_hours * 3600
        return {
            "status": self.status,
            "worked": _fmt_duration(worked),
            "worked_seconds": worked,
            "breaks": _fmt_duration(breaks),
            "break_seconds": breaks,
            "target": _fmt_duration(target),
            "remaining": _fmt_duration(max(0, target - worked)),
            "remaining_seconds": max(0, target - worked),
            "overtime": _fmt_duration(max(0, worked - target)),
            "check_in_time": (
                self._current.start.astimezone().strftime("%H:%M")
                if self._current
                else None
            ),
        }

    def format_status_line(self) -> str:
        s = self.summary_today()
        if s["status"] == "idle":
            return "Not checked in"
        status = "Break" if s["status"] == "break" else "Working"
        return f"{status}: {s['worked']} / {s['target']}  ·  Break: {s['breaks']}  ·  Remaining: {s['remaining']}"
