"""Working Time tracker page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.working_time import WorkingTimeService

if TYPE_CHECKING:
    from core.application import DevDeskApplication


class WorkingTimePage(QWidget):
    def __init__(self, app: "DevDeskApplication", parent=None) -> None:
        super().__init__(parent)
        self._app = app
        target = float(app.config.get("working_time.daily_target_hours", 8.0))
        self.service = WorkingTimeService(storage=app.storage, daily_target_hours=target)
        self._build()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(1000)
        self._refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        title = QLabel("Working Time")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        self.card = QFrame()
        self.card.setObjectName("card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)

        self.lbl_status = QLabel("Status: —")
        self.lbl_status.setStyleSheet("font-size: 16px; font-weight: 600;")
        card_layout.addWidget(self.lbl_status)

        self.lbl_time = QLabel("00:00:00 / 08:00:00")
        self.lbl_time.setObjectName("cardValue")
        card_layout.addWidget(self.lbl_time)

        self.lbl_detail = QLabel("Break: 00:00:00  ·  Remaining: 08:00:00")
        self.lbl_detail.setObjectName("cardSubtitle")
        card_layout.addWidget(self.lbl_detail)

        self.lbl_checkin = QLabel("")
        self.lbl_checkin.setObjectName("cardSubtitle")
        card_layout.addWidget(self.lbl_checkin)

        layout.addWidget(self.card)

        row = QHBoxLayout()
        self.btn_checkin = QPushButton("Check In")
        self.btn_checkin.clicked.connect(self._on_check_in)
        row.addWidget(self.btn_checkin)

        self.btn_checkout = QPushButton("Check Out")
        self.btn_checkout.setObjectName("secondary")
        self.btn_checkout.clicked.connect(self._on_check_out)
        row.addWidget(self.btn_checkout)

        self.btn_break = QPushButton("Start Break")
        self.btn_break.setObjectName("secondary")
        self.btn_break.clicked.connect(self._on_break)
        row.addWidget(self.btn_break)

        row.addStretch()
        layout.addLayout(row)

        note = QLabel(
            "All data is stored locally in JSON. Timer display updates every second; "
            "disk writes occur only on state changes."
        )
        note.setWordWrap(True)
        note.setObjectName("cardSubtitle")
        layout.addWidget(note)
        layout.addStretch()

    def _refresh(self) -> None:
        summary = self.service.summary_today()
        status = summary["status"]
        status_map = {"idle": "Not checked in", "working": "Working", "break": "On break"}
        self.lbl_status.setText(f"Status: {status_map.get(status, status)}")
        self.lbl_time.setText(f"{summary['worked']} / {summary['target']}")
        overtime = ""
        if summary["worked_seconds"] > self.service.daily_target_hours * 3600:
            overtime = f"  ·  Overtime: {summary['overtime']}"
        self.lbl_detail.setText(
            f"Break: {summary['breaks']}  ·  Remaining: {summary['remaining']}{overtime}"
        )
        if summary["check_in_time"]:
            self.lbl_checkin.setText(f"Checked in at {summary['check_in_time']}")
        else:
            self.lbl_checkin.setText("")

        is_idle = status == "idle"
        is_break = status == "break"
        self.btn_checkin.setEnabled(is_idle)
        self.btn_checkout.setEnabled(not is_idle)
        self.btn_break.setEnabled(not is_idle)
        self.btn_break.setText("End Break" if is_break else "Start Break")

        if self._app.tray:
            self._app.tray.update_tooltip(self.service.format_status_line())

        if self._app.main_window and hasattr(self._app.main_window, "page_overview"):
            ov = self._app.main_window.page_overview
            if hasattr(ov, "card_status"):
                ov.card_status.set_value(status_map.get(status, status), "Local tracker")
                ov.card_time.set_value(
                    f"{summary['worked']} / {summary['target']}",
                    f"Remaining: {summary['remaining']}",
                )

    def _on_check_in(self) -> None:
        try:
            self.service.check_in()
            self._refresh()
        except ValueError as exc:
            QMessageBox.warning(self, "Working Time", str(exc))

    def _on_check_out(self) -> None:
        try:
            self.service.check_out()
            self._refresh()
        except ValueError as exc:
            QMessageBox.warning(self, "Working Time", str(exc))

    def _on_break(self) -> None:
        try:
            if self.service.status == "break":
                self.service.end_break()
            else:
                self.service.start_break()
            self._refresh()
        except ValueError as exc:
            QMessageBox.warning(self, "Working Time", str(exc))
