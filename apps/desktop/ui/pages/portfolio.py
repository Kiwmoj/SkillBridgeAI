from typing import Any

from PyQt6.QtWidgets import QFileDialog, QLabel, QMessageBox, QPushButton, QTextEdit, QVBoxLayout

from apps.desktop.ui.components.formatting import AI_NOTICE
from apps.desktop.ui.components.widgets import add_action, text_label
from apps.desktop.ui.dialogs.records import choose_record
from apps.desktop.ui.pages.base import Page, PageContext


class PortfolioPage(Page):
    title = "Portfolio Reviewer"

    def __init__(self, context: PageContext) -> None:
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h1>Portfolio Reviewer</h1>"))
        layout.addWidget(text_label("Uploads are private. The first image frame is resized and metadata is stripped. "
                                    "Only the Review action sends an image to the AI provider."))
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        upload = QPushButton("Upload image privately")
        layout.addWidget(upload)
        add_action(layout, "Saved portfolio items", self.saved_items)
        layout.addWidget(self.output)
        upload.clicked.connect(self.upload_image)

    def upload_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.context.parent,
            "Select portfolio image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.gif)",
        )
        if not path:
            return
        self.run(
            lambda: self.backend.upload_portfolio(path),
            lambda result: self.output.setPlainText(f"{result['filename']} was saved. "
                                                    "Open Saved portfolio items to request AI feedback."),
        )

    def saved_items(self) -> None:
        choose_record(self, self.backend.portfolio_items, "Saved portfolio items", "filename", self.review_saved)

    def review_saved(self, item: dict[str, Any]) -> None:
        self.output.setPlainText(item.get("evaluation") or "No AI feedback saved yet.")
        if QMessageBox.question(self.context.parent, "Send image for AI review?", AI_NOTICE) != QMessageBox.StandardButton.Yes:
            return
        self.run(lambda: self.backend.evaluate_portfolio(item["id"]),
                 lambda result: self.output.setPlainText("AI-generated feedback\n\n" + result["evaluation"]),
                 self.show_in(self.output))
