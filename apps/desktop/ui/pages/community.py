from typing import Any

from PyQt6.QtWidgets import QCheckBox, QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout

from apps.desktop.ui.components.widgets import add_action, text_label
from apps.desktop.ui.dialogs.records import choose_record
from apps.desktop.ui.pages.base import Page, PageContext


class CommunityPage(Page):
    title = "Community"

    def __init__(self, context: PageContext) -> None:
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h1>Community Knowledge</h1>"))
        layout.addWidget(text_label("Approved submissions may be shown to users and sent as references for AI guidance. "
                                    "Training is separate and optional. Do not include anyone's private data."))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Contribution title")
        self.category = QLineEdit()
        self.category.setPlaceholderText("Category")
        self.source = QLineEdit()
        self.source.setPlaceholderText("Optional source URL or reference")
        self.body = QTextEdit()
        self.body.setPlaceholderText(
            "Share useful educational knowledge. Do not include private or sensitive information."
        )
        self.training_consent = QCheckBox(
            "I grant future permission to consider this contribution for reviewed training datasets"
        )
        self.copyright_confirmed = QCheckBox(
            "I own this material or have permission to submit it"
        )
        self.status = QTextEdit()
        self.status.setReadOnly(True)
        layout.addWidget(self.title_input)
        layout.addWidget(self.category)
        layout.addWidget(self.source)
        layout.addWidget(self.body)
        layout.addWidget(self.training_consent)
        layout.addWidget(self.copyright_confirmed)
        submit = QPushButton("Submit for review")
        layout.addWidget(submit)
        add_action(layout, "My submissions and permissions", self.my_submissions)
        layout.addWidget(self.status)
        submit.clicked.connect(self.submit_contribution)

    def my_submissions(self) -> None:
        choose_record(self, self.backend.my_contributions, "My submissions", "title", self.show_submission)

    def show_submission(self, item: dict[str, Any]) -> None:
        self.status.setPlainText(f"{item['title']}\nReview: {item['review_status']}\n"
                                 f"Future training permission: {'granted' if item['consent_to_training'] else 'not granted'}")
        self.change_permission(item)

    def change_permission(self, item: dict[str, Any]) -> None:
        action = "Withdraw" if item["consent_to_training"] else "Grant"
        label = f"{action} future training permission for this specific contribution?"
        if QMessageBox.question(self.context.parent, "Contribution permission", label) == QMessageBox.StandardButton.Yes:
            self.run(lambda: self.backend.set_contribution_consent(item["id"], not item["consent_to_training"]),
                     lambda _: self.notify("Contribution permission updated."))

    def submit_contribution(self) -> None:
        if len(self.body.toPlainText().strip()) < 20:
            QMessageBox.warning(self.context.parent, "Community contribution",
                                "The contribution body must contain at least 20 characters.")
            return
        payload = {
            "title": self.title_input.text().strip(),
            "category": self.category.text().strip(),
            "source": self.source.text().strip() or None,
            "body": self.body.toPlainText().strip(),
            "consent_to_training": self.training_consent.isChecked(),
            "copyright_confirmed": self.copyright_confirmed.isChecked(),
        }
        self.run(
            lambda: self.backend.submit_contribution(payload),
            lambda result: self.status.setPlainText(
                f"Submitted.\nReview status: {result['review_status']}\n"
                "This submission is not approved community knowledge or training data."
            ),
        )
