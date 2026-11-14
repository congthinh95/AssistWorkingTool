#!/usr/bin/env python3
"""DevDesk entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QSystemTrayIcon, QMessageBox

from core.application import DevDeskApplication
from core.logger import get_logger
from ui.tray import SystemTray
from ui.main_window import MainWindow


def main() -> int:
    app = DevDeskApplication(sys.argv)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            "DevDesk",
            "System tray is not available on this desktop environment.\n"
            "DevDesk requires a system tray to run.",
        )
        return 1

    tray = SystemTray(app)
    app.tray = tray

    window = MainWindow(app)
    app.main_window = window

    # Wire background services after UI exists
    app.init_services()

    # Load dashboard cards from any existing cache
    app._update_overview_cards()

    if not app.config.start_minimized:
        window.show()

    logger = get_logger("main")
    logger.info("DevDesk ready – tray icon active")

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
