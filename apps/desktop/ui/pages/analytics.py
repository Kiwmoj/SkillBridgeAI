from typing import Any

from PyQt6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout

from apps.desktop.ui.pages.base import Page, PageContext


class ProgressAnalyticsPage(Page):
    title = "Progress Analytics"

    def __init__(self, context: PageContext) -> None:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure

        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h1>Progress Analytics</h1>"))
        refresh = QPushButton("Refresh progress")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(refresh)
        self.canvas = FigureCanvasQTAgg(Figure(figsize=(7, 3), layout="constrained"))
        self.canvas.setMinimumHeight(190)
        layout.addWidget(self.canvas)
        layout.addWidget(self.output)
        refresh.clicked.connect(self.refresh)

    def refresh(self) -> None:
        self.run(self.backend.progress, self.show_progress)

    def show_progress(self, result: dict[str, Any]) -> None:
        self.output.setPlainText("\n".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in result.items()))
        self.canvas.figure.clear()
        axis = self.canvas.figure.subplots()
        axis.barh(["Roadmaps saved", "Projects completed", "Activities completed", "Portfolio items"],
                  [result["saved_roadmaps"], result["projects_completed"],
                   result["learning_activities_completed"], result["portfolio_total"]])
        axis.set_xlim(left=0)
        self.canvas.draw_idle()
