from typing import Any

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QInputDialog, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QVBoxLayout

from apps.desktop.ui.components.widgets import add_action, text_label
from apps.desktop.ui.dialogs.records import choose_record
from apps.desktop.ui.pages.base import Page, PageContext


class OpportunitiesPage(Page):
    title = "Opportunities & Colleges"

    def __init__(self, context: PageContext) -> None:
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h1>Opportunities & Colleges</h1>"))
        layout.addWidget(text_label("These are official search directories, not live listings. "
                                    "Check eligibility, deadlines, and availability at the source."))
        self.query = QLineEdit()
        self.query.setPlaceholderText("Career, college, or training topic")
        search = QPushButton("Find official starting points")
        self.results = QListWidget()
        save = QPushButton("Save selected opportunity")
        layout.addWidget(self.query)
        layout.addWidget(search)
        layout.addWidget(self.results)
        layout.addWidget(save)
        add_action(layout, "Open selected source", lambda: self.open_source(self.selected_item()))
        add_action(layout, "Saved opportunities and applications", self.saved_opportunities)
        self._opportunities: list[dict[str, Any]] = []
        search.clicked.connect(self.search_opportunities)
        save.clicked.connect(self.save_selected)

    def search_opportunities(self) -> None:
        search_query = self.query.text().strip()
        if not search_query:
            self.notify("Enter a career or education topic.")
            return
        self.run(lambda: self.backend.find_opportunities(search_query), self.show_opportunities)

    def show_opportunities(self, items: list[dict[str, Any]]) -> None:
        self._opportunities = items
        self.results.clear()
        for item in items:
            self.results.addItem(
                f"{item['title']} - {item['organization']}\n"
                f"{item['details']}\n{item['url']}"
            )

    def selected_item(self) -> dict[str, Any] | None:
        row = self.results.currentRow()
        if row < 0 or row >= len(self._opportunities):
            self.notify("Select a source first.")
            return None
        return self._opportunities[row]

    def save_selected(self) -> None:
        item = self.selected_item()
        if item is None:
            return
        self.run(
            lambda: self.backend.save_opportunity(item),
            lambda _: QMessageBox.information(self.context.parent, "Saved", "Opportunity saved."),
        )

    def open_source(self, record: dict[str, Any] | None) -> None:
        if record and record.get("url"):
            url = QUrl(record["url"])
            if url.isValid() and url.scheme() in {"http", "https"}:
                if not QDesktopServices.openUrl(url):
                    self.notify("The browser could not open this source.")

    def saved_opportunities(self) -> None:
        choose_record(self, self.backend.saved_opportunities, "Saved opportunities", "title",
                      self.update_application)

    def update_application(self, item: dict[str, Any]) -> None:
        states = ["saved", "preparing", "applied", "closed"]
        status, ok = QInputDialog.getItem(self.context.parent, "Application status", "Status:", states,
                                          states.index(item["application_status"]), editable=False)
        if ok and status != item["application_status"]:
            self.run(lambda: self.backend.update_opportunity(item["id"], status),
                     lambda _: self.notify("Application status saved."))
