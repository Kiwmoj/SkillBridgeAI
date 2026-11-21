from typing import Any

from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from apps.desktop.ui.components.widgets import add_action
from apps.desktop.ui.pages.base import Page, PageContext


class AdminPage(Page):
    title = "Administrator"

    def __init__(self, context: PageContext) -> None:
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h1>Administrator Control Panel</h1>"))

        self.dashboard = QTextEdit()
        self.dashboard.setReadOnly(True)
        refresh_dashboard = QPushButton("Refresh dashboard")

        self.contributions = QListWidget()
        self.public_title = QLineEdit()
        self.public_title.setPlaceholderText("Reviewed public title")
        self.public_body = QTextEdit()
        self.public_body.setPlaceholderText("Review and remove identifiers from the public text before approving.")
        self.public_body.setMaximumHeight(120)
        self.public_source = QLineEdit()
        self.public_source.setPlaceholderText("Reviewed source reference (optional)")
        self.submissions: list[dict[str, Any]] = []
        self.deidentified = QCheckBox("Confirmed de-identified")
        self.quality = QLineEdit()
        self.quality.setPlaceholderText("Quality rating from 3 to 5")
        self.review_notes = QTextEdit()
        self.review_notes.setPlaceholderText("Optional review notes")
        self.review_notes.setMaximumHeight(70)
        approve = QPushButton("Approve")
        reject = QPushButton("Reject")
        self.contributions.currentRowChanged.connect(self.select_submission)
        approve.clicked.connect(lambda: self.review("approved"))
        reject.clicked.connect(lambda: self.review("rejected"))
        refresh_dashboard.clicked.connect(self.refresh)
        import_button = QPushButton("Import official O*NET ZIP")
        import_button.clicked.connect(self.import_onet)

        layout.addWidget(refresh_dashboard)
        layout.addWidget(self.dashboard)
        layout.addWidget(QLabel("<b>Community moderation</b>"))
        layout.addWidget(self.contributions)
        layout.addWidget(self.public_title)
        layout.addWidget(self.public_body)
        layout.addWidget(self.public_source)
        layout.addWidget(self.deidentified)
        layout.addWidget(self.quality)
        layout.addWidget(self.review_notes)
        actions = QHBoxLayout()
        actions.addWidget(approve)
        actions.addWidget(reject)
        add_action(actions, "Review history", self.show_history)
        layout.addLayout(actions)
        operations = QHBoxLayout()
        operations.addWidget(import_button)
        add_action(operations, "Build reviewed draft", self.build_draft)
        add_action(operations, "Datasets and model records", self.show_pipeline)
        layout.addLayout(operations)

    def refresh(self) -> None:
        def load() -> tuple[Any, Any]:
            return self.backend.admin_dashboard(), self.backend.admin_contributions()

        def show(data: tuple[dict[str, Any], list[dict[str, Any]]]) -> None:
            metrics, items = data
            self.dashboard.setPlainText("\n".join(f"{key}: {value}" for key, value in metrics.items()))
            self.contributions.clear()
            self.submissions[:] = items
            for item in items:
                self.contributions.addItem(f"{item['id']} | {item['review_status']} | {item['title']}")

        self.run(load, show)

    def selected_id(self) -> Any:
        row = self.contributions.currentRow()
        return self.submissions[row]["id"] if 0 <= row < len(self.submissions) else None

    def select_submission(self, row: int) -> None:
        item = self.submissions[row] if 0 <= row < len(self.submissions) else {}
        self.public_title.setText(item.get("title", ""))
        self.public_body.setPlainText(item.get("body", ""))
        self.public_source.setText(item.get("source") or "")
        self.deidentified.setChecked(False)
        self.quality.clear()
        self.review_notes.clear()

    def review(self, status: str) -> None:
        identifier = self.selected_id()
        if not identifier:
            QMessageBox.warning(self.context.parent, "Moderation", "Select a community contribution.")
            return
        try:
            quality_rating = float(self.quality.text()) if self.quality.text().strip() else None
        except ValueError:
            QMessageBox.warning(self.context.parent, "Moderation", "Quality rating must be numeric.")
            return
        payload: dict[str, Any] = {
            "status": status,
            "deidentified": self.deidentified.isChecked(),
            "quality_rating": quality_rating,
            "notes": self.review_notes.toPlainText().strip() or None,
        }
        if status == "approved":
            payload.update(public_title=self.public_title.text().strip(),
                           public_body=self.public_body.toPlainText().strip(),
                           public_source=self.public_source.text().strip())
        self.run(lambda: self.backend.review_contribution(identifier, payload), lambda _: self.refresh())

    def show_history(self) -> None:
        identifier = self.selected_id()
        if not identifier:
            self.notify("Select a contribution.")
            return
        self.run(lambda: self.backend.contribution_history(identifier),
                 lambda items: self.dashboard.setPlainText(
                     "\n".join(f"{i['created_at']} | {i['status']} | {i.get('notes') or ''}" for i in items)
                     or "No review history."
                 ))

    def build_draft(self) -> None:
        name, ok = QInputDialog.getText(self.context.parent, "Prepare a dataset draft",
                                        "Version name (no model will be trained):")
        if ok:
            self.run(lambda: self.backend.build_dataset(name),
                     lambda info: self.dashboard.setPlainText(
                         f"Draft {info['name']}: {info['train_count']} training records and "
                         f"{info['validation_count']} validation records. No model trained."))

    def show_pipeline(self) -> None:
        def load() -> tuple[Any, Any, Any]:
            return self.backend.datasets(), self.backend.training_history(), self.backend.models()

        def show(groups: tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]) -> None:
            lines: list[str] = []
            for heading, records in zip(("Datasets", "Audit history", "Model records"), groups, strict=True):
                lines.extend((heading, ""))
                for record in records:
                    lines.append(f"{record.get('name') or record.get('action')} — {record['status']}")
                    if record.get("evaluation_summary"):
                        lines.append(record["evaluation_summary"])
                lines.append("")
            self.dashboard.setPlainText("\n".join(lines))

        self.run(load, show)

    def import_onet(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.context.parent,
            "Select official O*NET ZIP",
            "",
            "ZIP archives (*.zip)",
        )
        if not path:
            return
        version, ok = QInputDialog.getText(
            self.context.parent,
            "O*NET version",
            "Database version:",
        )
        if not ok:
            return
        dataset_version = version.strip() or "user-supplied"
        self.run(
            lambda: self.backend.import_onet(path, dataset_version),
            lambda result: self.dashboard.setPlainText(
                f"O*NET import completed: "
                f"{result['occupations']} occupations, "
                f"{result['alternate_titles']} alternate titles, "
                f"{result['descriptors']} descriptors\n"
                f"Version: {result['version']} | Skipped rows: {result['skipped_rows']}"
            ),
        )
