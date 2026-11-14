"""Daily Overview / Dashboard page."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from core.application import DevDeskApplication


class Card(QFrame):
    def __init__(self, title: str, value: str = "—", subtitle: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        layout.addWidget(self.title_label)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")
        layout.addWidget(self.value_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("cardSubtitle")
        layout.addWidget(self.subtitle_label)

    def set_value(self, value: str, subtitle: str = "") -> None:
        self.value_label.setText(value)
        if subtitle:
            self.subtitle_label.setText(subtitle)


class OverviewPage(QWidget):
    def __init__(self, app: "DevDeskApplication", parent=None) -> None:
        super().__init__(parent)
        self._app = app
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(16)

        # Header
        today = date.today().strftime("%A, %d %B %Y")
        header = QLabel(f"Daily Overview · {today}")
        header.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(header)

        # Cards grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(12)

        self.card_status = Card("Working Status", "Not checked in", "Local tracker")
        self.card_time = Card("Working Time Today", "00:00 / 08:00", "Remaining: 08:00")
        self.card_jira = Card("Jira Assigned", "—", "Connect Jira in Settings")
        self.card_overdue = Card("Jira Overdue", "—", "")
        self.card_pr_review = Card("PRs to Review", "—", "GitHub + Bitbucket")
        self.card_my_prs = Card("My Open PRs", "—", "")

        cards = [
            self.card_status,
            self.card_time,
            self.card_jira,
            self.card_overdue,
            self.card_pr_review,
            self.card_my_prs,
        ]
        for i, card in enumerate(cards):
            grid.addWidget(card, i // 3, i % 3)

        scroll.setWidget(container)
        root.addWidget(scroll, stretch=1)

        # Note
        note = QLabel(
            "Phase 1 foundation – local features and integrations will populate these cards."
        )
        note.setObjectName("cardSubtitle")
        note.setWordWrap(True)
        root.addWidget(note)
