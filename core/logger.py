"""Logging setup for DevDesk."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_logger_initialized = False


def setup_logging(
    log_dir: Optional[Path] = None,
    level: int = logging.INFO,
    console: bool = True,
) -> None:
    """Configure application-wide logging.

    Args:
        log_dir: Directory for log files. If None, only console logging is used.
        level: Logging level.
        console: Whether to also log to stderr.
    """
    global _logger_initialized
    if _logger_initialized:
        return

    root = logging.getLogger("devdesk")
    root.setLevel(level)
    root.handlers.clear()

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        root.addHandler(console_handler)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        root.addHandler(file_handler)

    _logger_initialized = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the devdesk namespace."""
    return logging.getLogger(f"devdesk.{name}" if not name.startswith("devdesk") else name)
