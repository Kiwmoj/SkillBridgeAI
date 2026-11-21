from typing import Any

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from apps.desktop.ui.components.widgets import Card, add_action
from apps.desktop.ui.pages.base import Page, PageContext

CARD_TITLES = ("Saved roadmaps", "Projects", "Learning activities", "Saved opportunities")


class DashboardPage(Page):
    title = "Dashboard"

    def __init__(self, context: PageContext) -> None:
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h1>Dashboard</h1><p>Your career development workspace</p>"))
        cards = QHBoxLayout()
        self.values: dict[str, QLabel] = {}
        for card_title in CARD_TITLES:
            card = Card(card_title)
            value = QLabel("Loading...")
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
        self.values["Learning activities"].setText(f"{result['learning_activities_completed']} completed")
        self.values["Saved opportunities"].setText(str(result["saved_opportunities"]))
