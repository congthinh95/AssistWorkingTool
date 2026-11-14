"""Application styles – light and dark themes inspired by Fluent Design."""

from __future__ import annotations

LIGHT_STYLESHEET = """
/* Global */
QWidget {
    font-family: "Segoe UI", "Ubuntu", "Noto Sans", sans-serif;
    font-size: 13px;
    color: #1a1a1a;
}

QMainWindow, QDialog {
    background-color: #f3f3f3;
}

/* Cards */
QFrame#card {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 12px;
}

QLabel#cardTitle {
    font-size: 14px;
    font-weight: 600;
    color: #1a1a1a;
}

QLabel#cardValue {
    font-size: 22px;
    font-weight: 600;
    color: #0078d4;
}

QLabel#cardSubtitle {
    font-size: 12px;
    color: #605e5c;
}

/* Navigation */
QListWidget#nav {
    background-color: #f9f9f9;
    border: none;
    border-right: 1px solid #e0e0e0;
    outline: none;
    padding: 8px 0;
}

QListWidget#nav::item {
    padding: 10px 16px;
    border-radius: 6px;
    margin: 2px 8px;
}

QListWidget#nav::item:selected {
    background-color: #e8f4fd;
    color: #0078d4;
    font-weight: 600;
}

QListWidget#nav::item:hover:!selected {
    background-color: #f0f0f0;
}

/* Buttons */
QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #106ebe;
}

QPushButton:pressed {
    background-color: #005a9e;
}

QPushButton:disabled {
    background-color: #c8c8c8;
    color: #6e6e6e;
}

QPushButton#secondary {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #d0d0d0;
}

QPushButton#secondary:hover {
    background-color: #f5f5f5;
}

/* Status bar */
QStatusBar {
    background-color: #f9f9f9;
    border-top: 1px solid #e0e0e0;
    color: #605e5c;
}
"""

DARK_STYLESHEET = """
/* Global */
QWidget {
    font-family: "Segoe UI", "Ubuntu", "Noto Sans", sans-serif;
    font-size: 13px;
    color: #e0e0e0;
}

QMainWindow, QDialog {
    background-color: #1e1e1e;
}

/* Cards */
QFrame#card {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 8px;
    padding: 12px;
}

QLabel#cardTitle {
    font-size: 14px;
    font-weight: 600;
    color: #f0f0f0;
}

QLabel#cardValue {
    font-size: 22px;
    font-weight: 600;
    color: #4cc2ff;
}

QLabel#cardSubtitle {
    font-size: 12px;
    color: #a0a0a0;
}

/* Navigation */
QListWidget#nav {
    background-color: #252525;
    border: none;
    border-right: 1px solid #3d3d3d;
    outline: none;
    padding: 8px 0;
}

QListWidget#nav::item {
    padding: 10px 16px;
    border-radius: 6px;
    margin: 2px 8px;
    color: #e0e0e0;
}

QListWidget#nav::item:selected {
    background-color: #0a3a5c;
    color: #4cc2ff;
    font-weight: 600;
}

QListWidget#nav::item:hover:!selected {
    background-color: #333333;
}

/* Buttons */
QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #1a86d9;
}

QPushButton:pressed {
    background-color: #005a9e;
}

QPushButton:disabled {
    background-color: #3d3d3d;
    color: #7a7a7a;
}

QPushButton#secondary {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #4d4d4d;
}

QPushButton#secondary:hover {
    background-color: #3a3a3a;
}

/* Status bar */
QStatusBar {
    background-color: #252525;
    border-top: 1px solid #3d3d3d;
    color: #a0a0a0;
}
"""


def get_stylesheet(theme: str = "system") -> str:
    """Return the stylesheet for the requested theme.

    theme: 'light' | 'dark' | 'system'
    """
    if theme == "system":
        # Simple heuristic – prefer dark on Linux if DESKTOP_SESSION hints dark,
        # otherwise light. Full system detection can be improved later.
        import os

        prefer_dark = os.environ.get("GTK_THEME", "").lower().endswith("-dark") or (
            os.environ.get("COLOR_SCHEME", "").lower() == "prefer-dark"
        )
        theme = "dark" if prefer_dark else "light"
    return DARK_STYLESHEET if theme == "dark" else LIGHT_STYLESHEET
