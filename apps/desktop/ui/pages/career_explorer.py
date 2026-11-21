from typing import Any

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from apps.desktop.ui.components.widgets import add_action
from apps.desktop.ui.dialogs.records import choose_record
from apps.desktop.ui.pages.base import Page, PageContext


class CareerExplorerPage(Page):
    title = "Career Explorer"

    def __init__(self, context: PageContext) -> None:
        super().__init__(context)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h1>Career Explorer</h1>"))

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Occupation title, code, or alternate title")
        search = QPushButton("Search")
        search.clicked.connect(self.search_careers)
        search_row.addWidget(self.search_input)
        search_row.addWidget(search)
        layout.addLayout(search_row)

        self.results = QTextEdit()
        self.results.setReadOnly(True)
        layout.addWidget(self.results)
        details = QHBoxLayout()
        self.detail_id = QLineEdit()
        self.detail_id.setPlaceholderText("Occupation ID from search")
        details.addWidget(self.detail_id)
        add_action(details, "Details", lambda: self.show_occupation(self.detail_id.text().strip()))
        add_action(details, "Save career", self.save_career)
        add_action(details, "Saved careers", self.saved_careers)
        layout.addLayout(details)

        layout.addWidget(QLabel("<b>Compare imported careers</b>"))
        compare_row = QHBoxLayout()
        self.compare_ids = QLineEdit()
        self.compare_ids.setPlaceholderText("Two to five occupation IDs, separated by commas")
        compare = QPushButton("Compare")
        compare.clicked.connect(self.compare_careers)
        compare_row.addWidget(self.compare_ids)
        compare_row.addWidget(compare)
        layout.addLayout(compare_row)

        layout.addWidget(QLabel("<b>Add a career outside O*NET</b>"))
        self.custom_title = QLineEdit()
        self.custom_title.setPlaceholderText("Custom occupation title")
        self.custom_industry = QLineEdit()
        self.custom_industry.setPlaceholderText("Industry")
        self.custom_description = QTextEdit()
        self.custom_description.setPlaceholderText("General description; this is not an official O*NET record")
        self.custom_description.setMaximumHeight(90)
        save_custom = QPushButton("Save custom occupation")
        save_custom.clicked.connect(self.save_custom_occupation)
        layout.addWidget(self.custom_title)
        layout.addWidget(self.custom_industry)
        layout.addWidget(self.custom_description)
        layout.addWidget(save_custom)
        add_action(layout, "View my custom occupations", self.custom_occupations)

    def search_careers(self) -> None:
        query = self.search_input.text().strip()
        self.run(lambda: self.backend.search_occupations(query), self.show_careers)

    def show_careers(self, items: list[dict[str, Any]]) -> None:
        if not items:
            self.results.setPlainText(
                "No occupation matched. An administrator must import an official "
                "O*NET archive before O*NET occupations become searchable."
            )
            return
        output = []
        for item in items:
            output.append(
                f"ID {item['id']} | {item['title']} ({item['onet_soc_code']})"
                f"\nO*NET version: {item['dataset_version'] or 'not recorded'}"
                f"\n{item['description'] or 'No description imported'}"
            )
        self.results.setPlainText("\n\n".join(output))

    def show_occupation(self, identifier: str) -> None:
        if not identifier.isdecimal():
            self.notify("Enter the occupation ID shown in search results.")
            return

        def describe(detail: dict[str, Any], category: str | None = None) -> None:
            occupation = detail["occupation"]
            attribution = detail["attribution"]
            text = (
                f"{occupation['title']} | {occupation['onet_soc_code']}\n"
                f"{attribution['credit']} {occupation['dataset_version']}\n{attribution['source_url']}\n"
                f"{attribution['license_url']} — {attribution['notice']}\n\n{occupation['description'] or ''}\n\n"
                f"Related: {', '.join(item['title'] or item['onet_soc_code'] for item in detail['related_occupations'])}\n\n"
                f"Showing {len(detail['descriptors'])} of {detail['descriptor_count']} descriptors:\n"
                + "\n".join(
                    f"{item['category']} | {item['name']}"
                    + (f" — {item['rating']} ({item['scale']})" if item["rating"] is not None else "")
                    + (f" — category {item['attributes']['Category']}" if "Category" in item["attributes"] else "")
                    for item in detail["descriptors"]
                )
            )
            self.results.setPlainText(text)
            if category is None and detail["categories"]:
                chosen, ok = QInputDialog.getItem(self.context.parent, "Occupational data", "View a category:",
                                                  detail["categories"], editable=False)
                if ok:
                    self.run(lambda: self.backend.occupation_detail(identifier, chosen, 500),
                             lambda result: describe(result, chosen))

        self.run(lambda: self.backend.occupation_detail(identifier), describe)

    def save_career(self) -> None:
        occupation = self.detail_id.text().strip()
        if not occupation.isdecimal():
            self.notify("Enter the numeric occupation ID from the search results.")
            return
        self.run(lambda: self.backend.save_career(occupation), lambda _: self.notify("Career saved."))

    def saved_careers(self) -> None:
        choose_record(self, self.backend.saved_careers, "Saved careers", "title",
                      lambda item: self.show_occupation(str(item["id"])))

    def compare_careers(self) -> None:
        try:
            ids = [int(value.strip()) for value in self.compare_ids.text().split(",") if value.strip()]
        except ValueError:
            QMessageBox.warning(self.context.parent, "Invalid comparison",
                                "Use numeric occupation IDs separated by commas.")
            return
        if len(ids) < 2:
            QMessageBox.warning(self.context.parent, "Invalid comparison", "Enter at least two occupation IDs.")
            return
        self.run(
            lambda: self.backend.compare_occupations(ids),
            lambda result: self.results.setPlainText(
                "\n\n".join(
                    f"{occupation['title']} ({occupation['onet_soc_code']})"
                    "\n"
                    + "\n".join(
                        f"{descriptor['category']}: {descriptor['name']}"
                        f" ({descriptor['rating']})"
                        for descriptor in occupation["top_descriptors"]
                    )
                    for occupation in result["occupations"]
                )
            ),
        )

    def save_custom_occupation(self) -> None:
        title = self.custom_title.text().strip()
        if not title:
            QMessageBox.warning(self.context.parent, "Custom occupation", "Enter an occupation title.")
            return
        payload = {
            "title": title,
            "industry": self.custom_industry.text().strip(),
            "description": self.custom_description.toPlainText().strip(),
        }
        self.run(
            lambda: self.backend.create_custom_occupation(payload),
            lambda _: QMessageBox.information(
                self.context.parent, "Saved", "Custom occupation saved. It is not an official O*NET record.",
            ),
        )

    def custom_occupations(self) -> None:
        choose_record(self, self.backend.custom_occupations, "Custom occupations", "title",
                      self.show_custom_occupation)

    def show_custom_occupation(self, item: dict[str, Any]) -> None:
        self.results.setPlainText(
            f"Custom occupation (not verified by O*NET)\n{item['title']}\n"
            f"{item.get('industry') or ''}\n\n{item.get('description') or ''}"
        )
