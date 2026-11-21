from PyQt6.QtWidgets import QLabel, QMessageBox, QPushButton, QTextEdit, QVBoxLayout

from apps.desktop.ui.components.formatting import AI_NOTICE, generated_text
from apps.desktop.ui.components.widgets import text_label
from apps.desktop.ui.pages.base import Page, PageContext


class RealityCheckPage(Page):
    """Generic AI guidance screen: a question box, a Generate button and the grounded answer."""

    title = "Career Reality Check"
    purpose = "Career Reality Check"
    placeholder = "Describe the career, work expectations, costs, training, or trade-offs you want to examine."

    def __init__(self, context: PageContext) -> None:
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h1>{self.title}</h1>"))
        layout.addWidget(text_label(AI_NOTICE))
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText(self.placeholder)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        button = QPushButton("Generate")
        layout.addWidget(self.input_box)
        layout.addWidget(button)
        layout.addWidget(self.output)
        button.clicked.connect(self.generate)

    def generate(self) -> None:
        question = self.input_box.toPlainText().strip()
        if not question:
            QMessageBox.warning(self.context.parent, self.title, "Enter a question or career context.")
            return
        self.run(
            lambda: self.backend.generate_guidance(self.purpose, question),
            lambda result: self.output.setPlainText(generated_text(result["answer"], result["sources"])),
            self.show_in(self.output),
        )
