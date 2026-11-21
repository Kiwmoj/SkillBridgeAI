from typing import Any

from PyQt6.QtWidgets import QFormLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout

from apps.desktop.ui.components.formatting import AI_NOTICE, generated_text
from apps.desktop.ui.components.widgets import add_action
from apps.desktop.ui.pages.base import Page, PageContext


class SkillGapPage(Page):
    title = "Skill Gap Analyzer"

    def __init__(self, context: PageContext) -> None:
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h1>Skill Gap Analyzer</h1>"))
        form = QFormLayout()
        self.occupation_id = QLineEdit()
        self.occupation_id.setPlaceholderText("Imported O*NET occupation ID")
        self.occupation_title = QLineEdit()
        self.occupation_title.setPlaceholderText("Occupation title")
        self.skills = QTextEdit()
        self.skills.setPlaceholderText("One skill per line")
        form.addRow("Occupation ID", self.occupation_id)
        form.addRow("Occupation title", self.occupation_title)
        form.addRow("Current skills", self.skills)
        layout.addLayout(form)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        analyze = QPushButton("Analyze")
        layout.addWidget(analyze)
        layout.addWidget(self.output)
        analyze.clicked.connect(self.analyze_gap)
        add_action(layout, "Ask AI for learning priorities", self.explain)

    def analyze_gap(self) -> None:
        identifier = self.occupation_id.text().strip()
        if identifier and not identifier.isdecimal():
            self.notify("Occupation ID must be a number.")
            return
        payload = {
            "occupation_id": int(identifier) if identifier else None,
            "occupation_title": self.occupation_title.text().strip() or None,
            "current_skills": [
                skill.strip()
                for skill in self.skills.toPlainText().splitlines()
                if skill.strip()
            ],
        }
        if not payload["occupation_id"] and not payload["occupation_title"]:
            QMessageBox.warning(self.context.parent, "Skill gap", "Enter an occupation ID or occupation title.")
            return
        self.run(lambda: self.backend.skill_gap(payload), self.show_report)

    def show_report(self, result: dict[str, Any]) -> None:
        self.output.setPlainText(
            f"Occupation: {result['occupation']}\n"
            f"Source: {result['source']}\n"
            f"{result.get('notice', '')}\n\n"
            "Strengths:\n"
            + (
                "\n".join(f"- {item['name']} ({item['rating']})" for item in result["strengths"])
                or "No matching imported skills found"
            )
            + "\n\nGaps:\n"
            + (
                "\n".join(f"- {item['name']} ({item['rating']})" for item in result["gaps"])
                or "No gaps can be identified from the available records."
            )
        )

    def explain(self) -> None:
        report = self.output.toPlainText()
        if not report:
            self.notify("Analyze your skills first.")
            return
        if QMessageBox.question(self.context.parent, "Send skill comparison?", AI_NOTICE) != QMessageBox.StandardButton.Yes:
            return
        question = "Use this self-reported skill comparison to suggest learning priorities:\n" + report[:4600]
        self.run(lambda: self.backend.generate_guidance("Skill gap guidance", question),
                 lambda result: self.output.setPlainText(
                     generated_text(result["answer"], result["sources"], result.get("generated", True))),
                 self.show_in(self.output))
