from typing import Any

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout

from apps.desktop.ui.components.formatting import AI_NOTICE, generated_text
from apps.desktop.ui.components.widgets import add_action, text_label
from apps.desktop.ui.dialogs.records import choose_record, edit_activity_dialog
from apps.desktop.ui.pages.base import Page, PageContext


class LearningRoadmapPage(Page):
    title = "Learning Roadmap"

    def __init__(self, context: PageContext) -> None:
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h1>Learning Roadmap</h1>"))
        layout.addWidget(text_label(AI_NOTICE))
        self.occupation = QLineEdit()
        self.occupation.setPlaceholderText("Occupation")
        self.interests = QLineEdit()
        self.interests.setPlaceholderText("Interests")
        self.skills = QTextEdit()
        self.skills.setPlaceholderText("Current skills, one per line")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        generate = QPushButton("Generate and save roadmap")
        layout.addWidget(self.occupation)
        layout.addWidget(self.interests)
        layout.addWidget(self.skills)
        layout.addWidget(generate)
        tools = QHBoxLayout()
        add_action(tools, "Saved roadmaps", self.saved_roadmaps)
        add_action(tools, "Add roadmap activity", self.add_activity)
        add_action(tools, "Update activity", self.update_activity)
        layout.addLayout(tools)
        layout.addWidget(self.output)
        generate.clicked.connect(self.generate_roadmap)

    def show_roadmap(self, item: dict[str, Any]) -> None:
        self.output.setPlainText(generated_text(item["content"], item["sources"]))

    def saved_roadmaps(self) -> None:
        choose_record(self, self.backend.roadmaps, "Saved roadmaps", "occupation_title", self.show_roadmap)

    def add_activity(self) -> None:
        choose_record(self, self.backend.roadmaps, "Choose a roadmap", "occupation_title",
                      lambda record: edit_activity_dialog(self, None, record["id"]))

    def update_activity(self) -> None:
        choose_record(self, self.backend.activities, "Learning activities", "title",
                      lambda record: edit_activity_dialog(self, record))

    def generate_roadmap(self) -> None:
        if not self.occupation.text().strip():
            QMessageBox.warning(self.context.parent, "Learning roadmap", "Enter an occupation.")
            return
        payload = {
            "occupation_title": self.occupation.text().strip(),
            "interests": self.interests.text().strip(),
            "current_skills": [
                skill.strip()
                for skill in self.skills.toPlainText().splitlines()
                if skill.strip()
            ],
        }
        self.run(lambda: self.backend.create_roadmap(payload), self.show_roadmap)
