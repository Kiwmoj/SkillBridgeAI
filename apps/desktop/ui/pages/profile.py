from typing import Any

from PyQt6.QtWidgets import QFormLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout

from apps.desktop.ui.pages.base import Page, PageContext


class ProfilePage(Page):
    title = "My Profile"

    def __init__(self, context: PageContext) -> None:
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h1>My Profile</h1>"))
        form = QFormLayout()
        self.education = QLineEdit()
        self.interests = QLineEdit()
        self.goals = QTextEdit()
        self.location = QLineEdit()
        form.addRow("Education", self.education)
        form.addRow("Interests", self.interests)
        form.addRow("Goals", self.goals)
        form.addRow("Location", self.location)
        layout.addLayout(form)
        save = QPushButton("Save profile")
        save.clicked.connect(self.save_profile)
        layout.addWidget(save)
        layout.addStretch()
        self.run(self.backend.get_profile, self.load_profile)

    def load_profile(self, profile: dict[str, Any]) -> None:
        self.education.setText(profile.get("education") or "")
        self.interests.setText(profile.get("interests") or "")
        self.goals.setPlainText(profile.get("goals") or "")
        self.location.setText(profile.get("location") or "")

    def save_profile(self) -> None:
        payload = {
            "education": self.education.text(),
            "interests": self.interests.text(),
            "goals": self.goals.toPlainText(),
            "location": self.location.text(),
        }
        self.run(
            lambda: self.backend.update_profile(payload),
            lambda _: QMessageBox.information(self.context.parent, "Saved", "Profile saved successfully."),
        )
