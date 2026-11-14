"""Platform abstraction layer for Windows and Linux."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .logger import get_logger

logger = get_logger("platform")


class Platform:
    """Small platform abstraction used throughout DevDesk."""

    @staticmethod
    def get_platform_name() -> str:
        """Return a short platform identifier: 'windows', 'linux', or 'other'."""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        if system == "linux":
            return "linux"
        return "other"

    @staticmethod
    def is_windows() -> bool:
        return Platform.get_platform_name() == "windows"

    @staticmethod
    def is_linux() -> bool:
        return Platform.get_platform_name() == "linux"

    @staticmethod
    def get_config_directory() -> Path:
        """Return the directory used for configuration and data.

        Windows: %APPDATA%/DevDesk
        Linux:   ~/.config/devdesk
        """
        if Platform.is_windows():
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "DevDesk"
            return Path.home() / "AppData" / "Roaming" / "DevDesk"
        # Linux / other
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            return Path(xdg) / "devdesk"
        return Path.home() / ".config" / "devdesk"

    @staticmethod
    def get_data_directory() -> Path:
        """Alias for config directory (single local data root)."""
        return Platform.get_config_directory()

    @staticmethod
    def get_cache_directory() -> Path:
        return Platform.get_config_directory() / "cache"

    @staticmethod
    def get_logs_directory() -> Path:
        return Platform.get_config_directory() / "logs"

    @staticmethod
    def open_file(path: str | Path) -> bool:
        """Open a file with the default application. Returns True on success."""
        path = Path(path)
        if not path.exists():
            logger.warning("Cannot open non-existent file: %s", path)
            return False
        try:
            if Platform.is_windows():
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(
                    ["xdg-open", str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            return True
        except Exception as exc:
            logger.error("Failed to open file %s: %s", path, exc)
            return False

    @staticmethod
    def open_folder(path: str | Path) -> bool:
        """Open a folder in the file manager. Returns True on success."""
        path = Path(path)
        if not path.exists() or not path.is_dir():
            logger.warning("Cannot open non-existent folder: %s", path)
            return False
        try:
            if Platform.is_windows():
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(
                    ["xdg-open", str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            return True
        except Exception as exc:
            logger.error("Failed to open folder %s: %s", path, exc)
            return False

    @staticmethod
    def launch_application(executable: str | Path, args: Optional[list[str]] = None) -> bool:
        """Launch an external application. Returns True if process started."""
        executable = str(executable)
        args = args or []
        try:
            if Platform.is_windows():
                # Prefer startfile for simple launch; fall back to Popen
                if not args:
                    os.startfile(executable)  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(
                        [executable, *args],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                    )
            else:
                subprocess.Popen(
                    [executable, *args],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            return True
        except Exception as exc:
            logger.error("Failed to launch %s: %s", executable, exc)
            return False

    @staticmethod
    def open_terminal(working_directory: Optional[str | Path] = None) -> bool:
        """Open a terminal, optionally in the given working directory."""
        cwd = str(working_directory) if working_directory else None
        try:
            if Platform.is_windows():
                # Prefer Windows Terminal, then PowerShell, then cmd
                candidates = [
                    ["wt.exe", "-d", cwd or os.getcwd()],
                    ["powershell.exe", "-NoExit", "-Command", f"cd '{cwd}'" if cwd else ""],
                    ["cmd.exe", "/K", f"cd /d {cwd}" if cwd else ""],
                ]
                for cmd in candidates:
                    exe = shutil.which(cmd[0])
                    if exe:
                        subprocess.Popen(
                            cmd,
                            cwd=cwd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                        )
                        return True
                return False
            else:
                # Common Linux terminals
                terminals = [
                    ["gnome-terminal", f"--working-directory={cwd}" if cwd else None],
                    ["konsole", f"--workdir={cwd}" if cwd else None],
                    ["xfce4-terminal", f"--working-directory={cwd}" if cwd else None],
                    ["xterm"],
                    ["x-terminal-emulator"],
                ]
                for term in terminals:
                    exe = shutil.which(term[0])
                    if exe:
                        cmd = [exe]
                        if len(term) > 1 and term[1]:
                            cmd.append(term[1])
                        subprocess.Popen(
                            cmd,
                            cwd=cwd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True,
                        )
                        return True
                return False
        except Exception as exc:
            logger.error("Failed to open terminal: %s", exc)
            return False

    @staticmethod
    def register_startup(app_name: str = "DevDesk", executable: Optional[str] = None) -> bool:
        """Register the application to start with the OS. Best-effort."""
        executable = executable or sys.executable
        try:
            if Platform.is_windows():
                import winreg  # type: ignore

                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_SET_VALUE,
                )
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{executable}"')
                winreg.CloseKey(key)
                return True
            else:
                # XDG Autostart
                autostart_dir = Path.home() / ".config" / "autostart"
                autostart_dir.mkdir(parents=True, exist_ok=True)
                desktop_file = autostart_dir / f"{app_name.lower()}.desktop"
                content = (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    f"Name={app_name}\n"
                    f"Exec={executable}\n"
                    "X-GNOME-Autostart-enabled=true\n"
                    "Hidden=false\n"
                )
                desktop_file.write_text(content, encoding="utf-8")
                return True
        except Exception as exc:
            logger.error("Failed to register startup: %s", exc)
            return False

    @staticmethod
    def remove_startup(app_name: str = "DevDesk") -> bool:
        """Remove OS startup registration. Best-effort."""
        try:
            if Platform.is_windows():
                import winreg  # type: ignore

                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_SET_VALUE,
                )
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
                winreg.CloseKey(key)
                return True
            else:
                desktop_file = Path.home() / ".config" / "autostart" / f"{app_name.lower()}.desktop"
                if desktop_file.exists():
                    desktop_file.unlink()
                return True
        except Exception as exc:
            logger.error("Failed to remove startup: %s", exc)
            return False

    @staticmethod
    def show_notification(title: str, message: str, icon: Optional[str] = None) -> bool:
        """Show a native desktop notification. Best-effort via Qt or platform tools."""
        # Actual Qt notification is handled higher up; this is a fallback.
        try:
            if Platform.is_linux():
                # Try notify-send
                if shutil.which("notify-send"):
                    cmd = ["notify-send", title, message]
                    if icon:
                        cmd.extend(["-i", icon])
                    subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True
            # Windows toast would require additional packages; rely on Qt.
            return False
        except Exception as exc:
            logger.debug("Platform notification fallback failed: %s", exc)
            return False
