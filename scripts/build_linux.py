#!/usr/bin/env python3
"""Build the Linux distribution bundle for DevDesk using PyInstaller."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC_DIR = ROOT / "spec"
APP_NAME = "DevDesk"


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ModuleNotFoundError:
        print("PyInstaller not found. Installing into the current environment...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyInstaller>=6.10.0"])


def clean_previous_artifacts() -> None:
    for folder in (DIST, BUILD, SPEC_DIR):
        if folder.exists():
            shutil.rmtree(folder)


def build() -> int:
    ensure_pyinstaller()
    clean_previous_artifacts()

    resources_src = ROOT / "resources"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(DIST),
        "--workpath",
        str(BUILD),
        "--specpath",
        str(SPEC_DIR),
        "--add-data",
        f"{resources_src}{os.pathsep}resources",
        str(ROOT / "main.py"),
    ]

    print("[DevDesk][Linux] Building package...")
    print("Command:", " ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(build())
