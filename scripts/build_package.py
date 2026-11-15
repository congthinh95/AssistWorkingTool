#!/usr/bin/env python3
"""Build the project package for the active platform.

This wrapper simplifies packaging by delegating to platform-specific scripts.
It defaults to the current OS and can be used for release automation.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def detect_target(default: str | None = None) -> str:
    if default:
        target = default.strip().lower()
        if target in {"windows", "linux"}:
            return target
        raise ValueError("Target must be 'windows' or 'linux'.")

    if sys.platform.startswith("win"):
        return "windows"
    return "linux"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DevDesk package for Linux or Windows.")
    parser.add_argument(
        "--target",
        choices=["auto", "linux", "windows"],
        default="auto",
        help="Choose the package target platform. 'auto' uses the current OS.",
    )
    args = parser.parse_args()

    target = detect_target(None if args.target == "auto" else args.target)
    script_name = "build_linux.py" if target == "linux" else "build_windows.py"
    script_path = ROOT / "scripts" / script_name

    print(f"[DevDesk] Building target package for: {target}")
    return subprocess.call([sys.executable, str(script_path)], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
