#!/usr/bin/env python3
"""Build Linux executable with PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "DevDesk",
        "--add-data",
        "resources:resources",
        str(ROOT / "main.py"),
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
