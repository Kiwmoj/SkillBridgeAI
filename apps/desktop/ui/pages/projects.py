from typing import Any

from PyQt6.QtWidgets import QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout

from apps.desktop.ui.components.formatting import AI_NOTICE, generated_text
from apps.desktop.ui.components.widgets import add_action, text_label
from apps.desktop.ui.dialogs.records import choose_record
from apps.desktop.ui.pages.base import Page, PageContext


class ProjectsPage(Page):
    title = "Project Generator"

    def __init__(self, context: PageContext) -> None:
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h1>Project Generator</h1>"))
        layout.addWidget(text_label(AI_NOTICE))
        self.occupation = QLineEdit()
        self.occupation.setPlaceholderText("Career or occupation")
        self.theme = QLineEdit()
        self.theme.setPlaceholderText("Optional project theme")
        self.experience = QLineEdit()
        self.experience.setPlaceholderText("Optional experience, learning goals, and available materials")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        generate = QPushButton("Generate and save project")
        layout.addWidget(self.occupation)
        layout.addWidget(self.theme)
        layout.addWidget(self.experience)
        layout.addWidget(generate)
        add_action(layout, "Saved projects and status", self.saved_projects)
        layout.addWidget(self.output)
        generate.clicked.connect(self.generate_project)

    def saved_projects(self) -> None:
        choose_record(self, self.backend.projects, "Saved projects", "title", self.show_project)

    def show_project(self, item: dict[str, Any]) -> None:
        self.output.setPlainText(f"{item['title']}\nStatus: {item['status']}\n\n{item['description']}")
        states = ["planned", "in_progress", "completed"]
        status, ok = QInputDialog.getItem(self.context.parent, "Project progress", "Update status:", states,
                                          states.index(item["status"]), editable=False)
        if ok and status != item["status"]:
            self.run(lambda: self.backend.update_project(item["id"], status),
                     lambda _: self.notify("Project status saved."))

    def generate_project(self) -> None:
        if not self.occupation.text().strip():
            QMessageBox.warning(self.context.parent, "Project generator", "Enter a career or occupation.")
            return
        payload = {
            "occupation": self.occupation.text().strip(),
            "title": self.theme.text().strip() or None,
            "experience": self.experience.text().strip(),
        }
        self.run(
            lambda: self.backend.create_project(payload),
            lambda result: self.output.setPlainText(generated_text(
                f"{result['title']}\n\n{result['description']}", result["sources"],
            )),
        )
