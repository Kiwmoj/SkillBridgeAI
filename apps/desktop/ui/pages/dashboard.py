from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from apps.desktop.ui.components.widgets import Card, add_action
from apps.desktop.ui.pages.base import Page, PageContext

# Card title -> accent colour for a bit of visual variety across the dashboard tiles.
CARD_ACCENTS = {
    "Saved roadmaps": "#6ea8ff",
    "Projects": "#8f7bef",
    "Learning activities": "#4fc3a1",
    "Saved opportunities": "#f2a65a",
}
CARD_TITLES = tuple(CARD_ACCENTS)


class DashboardPage(Page):
    title = "Dashboard"

    def __init__(self, context: PageContext) -> None:
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<span id='t' style='font-size:19pt;font-weight:800'>Dashboard</span>"
                                "<p style='color:#91a2c4'>Your career development workspace</p>"))
        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.values: dict[str, QLabel] = {}
        for card_title in CARD_TITLES:
            card = Card(card_title, accent=CARD_ACCENTS[card_title])
            value = QLabel("—")
            value.setObjectName("cardValue")
            value.setAlignment(Qt.AlignmentFlag.AlignLeft)
            card.body.addWidget(value)
            cards.addWidget(card)
            self.values[card_title] = value
        layout.addLayout(cards)
        add_action(layout, "Refresh dashboard", self.refresh)
        layout.addStretch()
        self.refresh()

    def refresh(self) -> None:
        self.run(self.backend.progress, self.show_progress)

    def show_progress(self, result: dict[str, Any]) -> None:
        self.values["Saved roadmaps"].setText(str(result["saved_roadmaps"]))
        self.values["Projects"].setText(f"{result['project_total']} total")
        self.values["Learning activities"].setText(f"{result['learning_activities_completed']} done")
        self.values["Saved opportunities"].setText(str(result["saved_opportunities"]))
