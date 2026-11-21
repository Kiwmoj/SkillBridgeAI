import sys
from collections.abc import Callable

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QCloseEvent, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop.services.api_client import ApiClient, ApiError
from desktop.workers import ApiWorker


BASE_NAV_ITEMS = [
    "Dashboard",
    "My Profile",
    "Career Explorer",
    "Career Reality Check",
    "Skill Gap Analyzer",
    "Learning Roadmap",
    "Portfolio Reviewer",
    "Project Generator",
    "Opportunities & Colleges",
    "Progress Analytics",
    "Community",
    "Settings",
]
AI_NOTICE = "AI requests use the configured provider. Only share material you are allowed to send; remove private information."


def text_label(value: str):
    label = QLabel(value)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    return label


def generated_text(answer, sources):
    lines = ["AI-generated guidance", "", answer, "", "Retrieved references (not generated):"]
    for source in sources:
        label = "Reviewed community contribution" if source["source_type"] == "community" else source["source_type"]
        lines.append(f"[{source['id']}] {source['title']} ({label})\n"
                     f"{source.get('reference') or ''}\n{source.get('url') or ''}\n{source['text']}")
    if not sources:
        lines.append("No relevant references were retrieved. Treat this as general guidance.")
    return "\n".join(lines)


def add_action(layout, label, action):
    button = QPushButton(label)
    button.clicked.connect(action)
    layout.addWidget(button)
    return button


class Card(QWidget):
    def __init__(self, title: str):
        super().__init__()
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        layout.addWidget(heading)
        self.body = QVBoxLayout()
        layout.addLayout(self.body)


class LoginWindow(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self.authenticated: Callable[[dict], None] | None = None
        self._main_window: MainWindow | None = None
        self._worker = None
        self.setWindowTitle("SkillBridge AI")
        self.resize(460, 360)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "<h1>SkillBridge AI</h1>"
                "<p>Career development for every occupation</p>"
            )
        )
        self.name = QLineEdit()
        self.name.setPlaceholderText("Full name")
        self.email = QLineEdit()
        self.email.setPlaceholderText("Email")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.server = QLineEdit(api.base_url)
        self.server.setPlaceholderText("Backend URL")
        layout.addWidget(text_label("Backend address"))
        layout.addWidget(self.server)
        layout.addWidget(self.name)
        layout.addWidget(self.email)
        layout.addWidget(self.password)

        actions = QHBoxLayout()
        login_button = QPushButton("Sign in")
        register_button = QPushButton("Create account")
        login_button.clicked.connect(self.login)
        register_button.clicked.connect(self.register)
        actions.addWidget(login_button)
        actions.addWidget(register_button)
        layout.addLayout(actions)
        add_action(layout, "Reset password with recovery code", self.reset_password)

        self.status = text_label("")
        layout.addWidget(self.status)

    def login(self):
        email, password = self.email.text().strip(), self.password.text()
        self.run_request(lambda: self.api.login(email, password), self.finish_auth, "Signing in...")

    def register(self):
        if not self.name.text().strip():
            self.status.setText("Enter your name to create an account.")
            return
        name, email, password = self.name.text().strip(), self.email.text().strip(), self.password.text()
        self.run_request(lambda: self.api.register(name, email, password), self.finish_auth, "Creating account...")

    def run_request(self, operation, on_success, status):
        if self._worker is not None:
            return
        try:
            self.api.set_backend_url(self.server.text())
        except ApiError as exc:
            self.status.setText(str(exc))
            return
        self.status.setText(status)
        self.setEnabled(False)
        worker = ApiWorker(operation, self)
        self._worker = worker

        def finished():
            self._worker = None
            self.setEnabled(True)
            worker.deleteLater()
            if worker.error:
                self.status.setText(worker.error)
            else:
                on_success(worker.result)

        worker.finished.connect(finished)
        worker.start()

    def closeEvent(self, a0: QCloseEvent | None):
        if self._worker is not None and a0 is not None:
            a0.ignore()
        else:
            super().closeEvent(a0)

    def reset_password(self):
        email = self.email.text().strip()
        if not email:
            self.status.setText("Enter your account email first.")
            return
        code, ok = QInputDialog.getText(self, "Password recovery", "Saved one-time recovery code:")
        if not ok:
            return
        password, ok = QInputDialog.getText(self, "Password recovery", "New password:", QLineEdit.EchoMode.Password)
        if ok:
            self.run_request(lambda: self.api.post("/auth/reset-password", {
                "email": email, "recovery_code": code, "password": password,
            }), lambda _: self.status.setText("Password reset. You can sign in now."), "Resetting password...")

    def finish_auth(self, result):
        self.api.set_token(result["access_token"])
        self.password.clear()
        self.status.clear()
        if callable(self.authenticated):
            self.authenticated(result)


class MainWindow(QMainWindow):
    def __init__(self, api: ApiClient, role: str, signed_out: Callable[[], None] | None = None):
        super().__init__()
        self.api = api
        self.role = role
        self.signed_out = signed_out
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.setWindowTitle("SkillBridge AI")
        self.resize(1280, 820)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        brand = QLabel("SKILLBRIDGE")
        brand.setObjectName("brand")
        sidebar_layout.addWidget(brand)

        nav_items = list(BASE_NAV_ITEMS)
        if role == "admin":
            nav_items.append("Administrator")
        self.nav = QListWidget()
        self.nav.addItems(nav_items)
        self.nav.setObjectName("nav")
        sidebar_layout.addWidget(self.nav)
        sidebar_layout.addStretch()

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self._active_workers = []
        self.loading = QProgressBar()
        self.loading.setRange(0, 100)
        self.loading.setValue(100)
        self.loading.setObjectName("loading")
        self.stack = QStackedWidget()
        pages = [
            self.dashboard_page(),
            self.profile_page(),
            self.career_page(),
            self.reality_page(),
            self.skill_gap_page(),
            self.roadmap_page(),
            self.portfolio_page(),
            self.project_page(),
            self.opportunity_page(),
            self.progress_page(),
            self.community_page(),
            self.settings_page(),
        ]
        if role == "admin":
            pages.append(self.admin_page())
        for page in pages:
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)
        right_layout.addWidget(self.stack, 1)
        right_layout.addWidget(self.loading)

        layout.addWidget(sidebar)
        layout.addWidget(right, 1)

    def run_worker(self, operation, callback, on_error=None):
        self.stack.setEnabled(False)
        self.loading.setRange(0, 0)
        self.status_bar.showMessage("Working...")
        worker = ApiWorker(operation, self)

        def finished():
            self._active_workers.remove(worker)
            if not self._active_workers:
                self.stack.setEnabled(True)
                self.loading.setRange(0, 100)
                self.loading.setValue(100)
            worker.deleteLater()
            if worker.error:
                if on_error:
                    on_error(worker.error)
                else:
                    self.status_bar.showMessage(worker.error)
            else:
                self.status_bar.clearMessage()
                callback(worker.result)

        worker.finished.connect(finished)
        self._active_workers.append(worker)
        worker.start()

    def closeEvent(self, a0: QCloseEvent | None):
        if self._active_workers and a0 is not None:
            self.status_bar.showMessage("Wait for the current request before closing.")
            a0.ignore()
        else:
            super().closeEvent(a0)

    def choose_record(self, route, title, label, action):
        def show(items):
            if not items:
                self.status_bar.showMessage(f"No records to show: {title}.")
                return
            entries = [f"{item['id']} | {item.get(label) or 'Untitled'}" for item in items]
            selected, ok = QInputDialog.getItem(self, title, "Select a record:", entries, editable=False)
            if ok:
                action(items[entries.index(selected)])
        self.run_worker(lambda: self.api.get(route), show)

    def dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(
            QLabel("<h1>Dashboard</h1><p>Your career development workspace</p>")
        )
        cards = QHBoxLayout()
        self.dashboard_content = {}
        for title in (
            "Saved roadmaps",
            "Projects",
            "Learning activities",
            "Saved opportunities",
        ):
            card = Card(title)
            value = QLabel("Loading...")
            card.body.addWidget(value)
            cards.addWidget(card)
            self.dashboard_content[title] = value
        layout.addLayout(cards)
        add_action(layout, "Refresh dashboard", lambda: self.run_worker(
            lambda: self.api.get("/progress"), self.load_dashboard,
        ))
        layout.addStretch()
        self.run_worker(
            lambda: self.api.get("/progress"),
            self.load_dashboard,
        )
        return page

    def load_dashboard(self, result):
        self.dashboard_content["Saved roadmaps"].setText(
            str(result["saved_roadmaps"])
        )
        self.dashboard_content["Projects"].setText(
            f"{result['project_total']} total"
        )
        self.dashboard_content["Learning activities"].setText(
            f"{result['learning_activities_completed']} completed"
        )
        self.dashboard_content["Saved opportunities"].setText(
            str(result["saved_opportunities"])
        )

    def profile_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h1>My Profile</h1>"))
        form = QFormLayout()
        self.profile_education = QLineEdit()
        self.profile_interests = QLineEdit()
        self.profile_goals = QTextEdit()
        self.profile_location = QLineEdit()
        form.addRow("Education", self.profile_education)
        form.addRow("Interests", self.profile_interests)
        form.addRow("Goals", self.profile_goals)
        form.addRow("Location", self.profile_location)
        layout.addLayout(form)
        save = QPushButton("Save profile")
        save.clicked.connect(self.save_profile)
        layout.addWidget(save)
        layout.addStretch()
        self.run_worker(
            lambda: self.api.get("/profile"),
            self.load_profile,
        )
        return page

    def load_profile(self, profile):
        self.profile_education.setText(profile.get("education") or "")
        self.profile_interests.setText(profile.get("interests") or "")
        self.profile_goals.setPlainText(profile.get("goals") or "")
        self.profile_location.setText(profile.get("location") or "")

    def save_profile(self):
        payload = {
            "education": self.profile_education.text(),
            "interests": self.profile_interests.text(),
            "goals": self.profile_goals.toPlainText(),
            "location": self.profile_location.text(),
        }
        self.run_worker(
            lambda: self.api.put("/profile", payload),
            lambda _: QMessageBox.information(
                self,
                "Saved",
                "Profile saved successfully.",
            ),
        )

    def career_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h1>Career Explorer</h1>"))

        search_row = QHBoxLayout()
        self.career_search = QLineEdit()
        self.career_search.setPlaceholderText(
            "Occupation title, code, or alternate title"
        )
        search = QPushButton("Search")
        search.clicked.connect(self.search_careers)
        search_row.addWidget(self.career_search)
        search_row.addWidget(search)
        layout.addLayout(search_row)

        self.career_results = QTextEdit()
        self.career_results.setReadOnly(True)
        layout.addWidget(self.career_results)
        details = QHBoxLayout()
        detail_id = QLineEdit()
        detail_id.setPlaceholderText("Occupation ID from search")
        details.addWidget(detail_id)
        add_action(details, "Details", lambda: self.show_occupation(detail_id.text().strip()))
        def save_career():
            occupation = detail_id.text().strip()
            if not occupation.isdecimal():
                self.status_bar.showMessage("Enter the numeric occupation ID from the search results.")
                return
            self.run_worker(lambda: self.api.put(f"/occupations/saved/{occupation}"),
                            lambda _: self.status_bar.showMessage("Career saved."))
        add_action(details, "Save career", save_career)
        add_action(details, "Saved careers", lambda: self.choose_record(
            "/occupations/saved", "Saved careers", "title",
            lambda item: self.show_occupation(str(item["id"])),
        ))
        layout.addLayout(details)

        layout.addWidget(QLabel("<b>Compare imported careers</b>"))
        compare_row = QHBoxLayout()
        self.compare_ids = QLineEdit()
        self.compare_ids.setPlaceholderText(
            "Two to five occupation IDs, separated by commas"
        )
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
        self.custom_description.setPlaceholderText(
            "General description; this is not an official O*NET record"
        )
        self.custom_description.setMaximumHeight(90)
        save_custom = QPushButton("Save custom occupation")
        save_custom.clicked.connect(self.save_custom_occupation)
        layout.addWidget(self.custom_title)
        layout.addWidget(self.custom_industry)
        layout.addWidget(self.custom_description)
        layout.addWidget(save_custom)
        add_action(layout, "View my custom occupations", lambda: self.choose_record(
            "/custom-occupations", "Custom occupations", "title",
            lambda item: self.career_results.setPlainText(
                f"Custom occupation (not verified by O*NET)\n{item['title']}\n"
                f"{item.get('industry') or ''}\n\n{item.get('description') or ''}"
            ),
        ))
        return page

    def show_occupation(self, identifier):
        if not identifier.isdecimal():
            self.status_bar.showMessage("Enter the occupation ID shown in search results.")
            return
        path = f"/occupations/{identifier}"

        def describe(detail, category=None):
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
            self.career_results.setPlainText(text)
            if category is None and detail["categories"]:
                chosen, ok = QInputDialog.getItem(self, "Occupational data", "View a category:",
                                                  detail["categories"], editable=False)
                if ok:
                    self.run_worker(lambda: self.api.get(path, {"category": chosen, "limit": 500}),
                                    lambda result: describe(result, chosen))

        self.run_worker(lambda: self.api.get(path), describe)

    def search_careers(self):
        query = self.career_search.text().strip()
        self.run_worker(
            lambda: self.api.get("/occupations/search", {"q": query}),
            self.show_careers,
        )

    def show_careers(self, items):
        if not items:
            self.career_results.setPlainText(
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
        self.career_results.setPlainText("\n\n".join(output))

    def compare_careers(self):
        try:
            ids = [
                int(value.strip())
                for value in self.compare_ids.text().split(",")
                if value.strip()
            ]
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid comparison",
                "Use numeric occupation IDs separated by commas.",
            )
            return
        if len(ids) < 2:
            QMessageBox.warning(
                self,
                "Invalid comparison",
                "Enter at least two occupation IDs.",
            )
            return
        self.run_worker(
            lambda: self.api.post("/occupations/compare", {"occupation_ids": ids}),
            lambda result: self.career_results.setPlainText(
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

    def save_custom_occupation(self):
        title = self.custom_title.text().strip()
        if not title:
            QMessageBox.warning(
                self,
                "Custom occupation",
                "Enter an occupation title.",
            )
            return
        payload = {
            "title": title,
            "industry": self.custom_industry.text().strip(),
            "description": self.custom_description.toPlainText().strip(),
        }
        self.run_worker(
            lambda: self.api.post("/custom-occupations", payload),
            lambda _: QMessageBox.information(
                self,
                "Saved",
                "Custom occupation saved. It is not an official O*NET record.",
            ),
        )

    def generic_ai_page(self, title: str, purpose: str, placeholder: str):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(f"<h1>{title}</h1>"))
        layout.addWidget(text_label(AI_NOTICE))
        input_box = QTextEdit()
        input_box.setPlaceholderText(placeholder)
        output = QTextEdit()
        output.setReadOnly(True)
        button = QPushButton("Generate")
        layout.addWidget(input_box)
        layout.addWidget(button)
        layout.addWidget(output)

        def generate():
            question = input_box.toPlainText().strip()
            if not question:
                QMessageBox.warning(self, title, "Enter a question or career context.")
                return
            self.run_worker(
                lambda: self.api.post(
                    "/ai/generate",
                    {"purpose": purpose, "question": question},
                ),
                lambda result: output.setPlainText(generated_text(result["answer"], result["sources"])),
            )

        button.clicked.connect(generate)
        return page

    def reality_page(self):
        return self.generic_ai_page(
            "Career Reality Check",
            "Career Reality Check",
            "Describe the career, work expectations, costs, training, or trade-offs you want to examine.",
        )

    def skill_gap_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h1>Skill Gap Analyzer</h1>"))
        form = QFormLayout()
        occupation_id = QLineEdit()
        occupation_id.setPlaceholderText("Imported O*NET occupation ID")
        occupation_title = QLineEdit()
        occupation_title.setPlaceholderText("Occupation title")
        skills = QTextEdit()
        skills.setPlaceholderText("One skill per line")
        form.addRow("Occupation ID", occupation_id)
        form.addRow("Occupation title", occupation_title)
        form.addRow("Current skills", skills)
        layout.addLayout(form)
        output = QTextEdit()
        output.setReadOnly(True)
        analyze = QPushButton("Analyze")
        layout.addWidget(analyze)
        layout.addWidget(output)

        def analyze_gap():
            identifier = occupation_id.text().strip()
            if identifier and not identifier.isdecimal():
                self.status_bar.showMessage("Occupation ID must be a number.")
                return
            payload = {
                "occupation_id": int(identifier) if identifier else None,
                "occupation_title": occupation_title.text().strip() or None,
                "current_skills": [
                    skill.strip()
                    for skill in skills.toPlainText().splitlines()
                    if skill.strip()
                ],
            }
            if not payload["occupation_id"] and not payload["occupation_title"]:
                QMessageBox.warning(
                    self,
                    "Skill gap",
                    "Enter an occupation ID or occupation title.",
                )
                return
            self.run_worker(
                lambda: self.api.post("/skill-gap", payload),
                lambda result: output.setPlainText(
                    f"Occupation: {result['occupation']}\n"
                    f"Source: {result['source']}\n"
                    f"{result.get('notice', '')}\n\n"
                    "Strengths:\n"
                    + (
                        "\n".join(
                            f"- {item['name']} ({item['rating']})"
                            for item in result["strengths"]
                        )
                        or "No matching imported skills found"
                    )
                    + "\n\nGaps:\n"
                    + (
                        "\n".join(
                            f"- {item['name']} ({item['rating']})"
                            for item in result["gaps"]
                        )
                        or "No gaps can be identified from the available records."
                    )
                ),
            )

        analyze.clicked.connect(analyze_gap)
        def explain():
            report = output.toPlainText()
            if not report:
                self.status_bar.showMessage("Analyze your skills first.")
                return
            if QMessageBox.question(self, "Send skill comparison?", AI_NOTICE) != QMessageBox.StandardButton.Yes:
                return
            question = "Use this self-reported skill comparison to suggest learning priorities:\n" + report[:4600]
            self.run_worker(lambda: self.api.post("/ai/generate", {"question": question, "purpose": "Skill gap guidance"}),
                            lambda result: output.setPlainText(generated_text(result["answer"], result["sources"])))
        add_action(layout, "Ask AI for learning priorities", explain)
        return page

    def roadmap_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h1>Learning Roadmap</h1>"))
        layout.addWidget(text_label(AI_NOTICE))
        occupation = QLineEdit()
        occupation.setPlaceholderText("Occupation")
        interests = QLineEdit()
        interests.setPlaceholderText("Interests")
        skills = QTextEdit()
        skills.setPlaceholderText("Current skills, one per line")
        output = QTextEdit()
        output.setReadOnly(True)
        generate = QPushButton("Generate and save roadmap")
        layout.addWidget(occupation)
        layout.addWidget(interests)
        layout.addWidget(skills)
        layout.addWidget(generate)
        tools = QHBoxLayout()
        add_action(tools, "Saved roadmaps", lambda: self.choose_record(
            "/roadmaps", "Saved roadmaps", "occupation_title",
            lambda item: output.setPlainText(generated_text(item["content"], item["sources"])),
        ))
        add_action(tools, "Add roadmap activity", lambda: self.choose_record(
            "/roadmaps", "Choose a roadmap", "occupation_title",
            lambda record: self.edit_activity(None, record["id"]),
        ))
        add_action(tools, "Update activity", lambda: self.choose_record(
            "/activities", "Learning activities", "title", self.edit_activity,
        ))
        layout.addLayout(tools)
        layout.addWidget(output)

        def generate_roadmap():
            if not occupation.text().strip():
                QMessageBox.warning(
                    self,
                    "Learning roadmap",
                    "Enter an occupation.",
                )
                return
            payload = {
                "occupation_title": occupation.text().strip(),
                "interests": interests.text().strip(),
                "current_skills": [
                    skill.strip()
                    for skill in skills.toPlainText().splitlines()
                    if skill.strip()
                ],
            }
            self.run_worker(
                lambda: self.api.post("/roadmaps", payload),
                lambda result: output.setPlainText(generated_text(result["content"], result["sources"])),
            )

        generate.clicked.connect(generate_roadmap)
        return page

    def edit_activity(self, record, roadmap_id=None):
        details = record or {}
        title, ok = QInputDialog.getText(self, "Learning activity", "Activity:", text=details.get("title", ""))
        if not ok:
            return
        states = ["not_started", "in_progress", "paused", "completed"]
        status, ok = QInputDialog.getItem(self, "Learning activity", "Status:", states,
                                          states.index(details.get("status", "not_started")), editable=False)
        if not ok:
            return
        notes, ok = QInputDialog.getMultiLineText(self, "Learning activity", "Notes:", details.get("notes") or "")
        if not ok:
            return
        payload = {"title": title, "status": status, "notes": notes,
                   "roadmap_id": details.get("roadmap_id", roadmap_id)}
        operation = (lambda: self.api.patch(f"/activities/{details['id']}", payload)) if record else (
            lambda: self.api.post("/activities", payload)
        )
        self.run_worker(operation, lambda _: self.status_bar.showMessage("Learning activity saved."))

    def portfolio_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h1>Portfolio Reviewer</h1>"))
        layout.addWidget(text_label("Uploads are private. The first image frame is resized and metadata is stripped. "
                                    "Only the Review action sends an image to the AI provider."))
        output = QTextEdit()
        output.setReadOnly(True)
        upload = QPushButton("Upload image privately")
        layout.addWidget(upload)
        add_action(layout, "Saved portfolio items", lambda: self.choose_record(
            "/portfolio", "Saved portfolio items", "filename",
            lambda item: review_saved(item),
        ))
        layout.addWidget(output)

        def upload_image():
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Select portfolio image",
                "",
                "Images (*.png *.jpg *.jpeg *.webp *.gif)",
            )
            if not path:
                return

            self.run_worker(
                lambda: self.api.upload("/portfolio/upload", path),
                lambda result: output.setPlainText(f"{result['filename']} was saved. "
                                                    "Open Saved portfolio items to request AI feedback."),
            )

        def review_saved(item):
            output.setPlainText(item.get("evaluation") or "No AI feedback saved yet.")
            if QMessageBox.question(self, "Send image for AI review?", AI_NOTICE) != QMessageBox.StandardButton.Yes:
                return
            self.run_worker(lambda: self.api.post(f"/portfolio/{item['id']}/evaluate", {"send_to_provider": True}),
                            lambda result: output.setPlainText("AI-generated feedback\n\n" + result["evaluation"]))

        upload.clicked.connect(upload_image)
        return page

    def project_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h1>Project Generator</h1>"))
        layout.addWidget(text_label(AI_NOTICE))
        occupation = QLineEdit()
        occupation.setPlaceholderText("Career or occupation")
        theme = QLineEdit()
        theme.setPlaceholderText("Optional project theme")
        experience = QLineEdit()
        experience.setPlaceholderText("Optional experience, learning goals, and available materials")
        output = QTextEdit()
        output.setReadOnly(True)
        generate = QPushButton("Generate and save project")
        layout.addWidget(occupation)
        layout.addWidget(theme)
        layout.addWidget(experience)
        layout.addWidget(generate)
        add_action(layout, "Saved projects and status", lambda: self.choose_record(
            "/projects", "Saved projects", "title", show_project,
        ))
        layout.addWidget(output)

        def show_project(item):
            output.setPlainText(f"{item['title']}\nStatus: {item['status']}\n\n{item['description']}")
            states = ["planned", "in_progress", "completed"]
            status, ok = QInputDialog.getItem(self, "Project progress", "Update status:", states,
                                              states.index(item["status"]), editable=False)
            if ok and status != item["status"]:
                self.run_worker(lambda: self.api.patch(f"/projects/{item['id']}", {"status": status}),
                                lambda _: self.status_bar.showMessage("Project status saved."))

        def generate_project():
            if not occupation.text().strip():
                QMessageBox.warning(
                    self,
                    "Project generator",
                    "Enter a career or occupation.",
                )
                return
            payload = {
                "occupation": occupation.text().strip(),
                "title": theme.text().strip() or None,
                "experience": experience.text().strip(),
            }
            self.run_worker(
                lambda: self.api.post("/projects", payload),
                lambda result: output.setPlainText(generated_text(
                    f"{result['title']}\n\n{result['description']}", result["sources"],
                )),
            )

        generate.clicked.connect(generate_project)
        return page

    def opportunity_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h1>Opportunities & Colleges</h1>"))
        layout.addWidget(text_label("These are official search directories, not live listings. "
                                    "Check eligibility, deadlines, and availability at the source."))
        query = QLineEdit()
        query.setPlaceholderText("Career, college, or training topic")
        search = QPushButton("Find official starting points")
        self.opportunity_results = QListWidget()
        save = QPushButton("Save selected opportunity")
        layout.addWidget(query)
        layout.addWidget(search)
        layout.addWidget(self.opportunity_results)
        layout.addWidget(save)
        add_action(layout, "Open selected source", lambda: self.open_source(selected_item()))
        add_action(layout, "Saved opportunities and applications", lambda: self.choose_record(
            "/opportunities/saved", "Saved opportunities", "title", update_application,
        ))
        self._opportunities = []

        def find():
            search_query = query.text().strip()
            if not search_query:
                self.status_bar.showMessage("Enter a career or education topic.")
                return
            self.run_worker(
                lambda: self.api.get(
                    "/opportunities",
                    {"q": search_query},
                ),
                self.show_opportunities,
            )

        def selected_item():
            row = self.opportunity_results.currentRow()
            if row < 0 or row >= len(self._opportunities):
                self.status_bar.showMessage("Select a source first.")
                return
            return self._opportunities[row]

        def save_selected():
            item = selected_item()
            if item is None:
                return
            self.run_worker(
                lambda: self.api.post("/opportunities/save", item),
                lambda _: QMessageBox.information(
                    self,
                    "Saved",
                    "Opportunity saved.",
                ),
            )

        def update_application(item):
            states = ["saved", "preparing", "applied", "closed"]
            status, ok = QInputDialog.getItem(self, "Application status", "Status:", states,
                                              states.index(item["application_status"]), editable=False)
            if ok and status != item["application_status"]:
                self.run_worker(lambda: self.api.patch(
                    f"/opportunities/saved/{item['id']}", {"application_status": status},
                ), lambda _: self.status_bar.showMessage("Application status saved."))

        search.clicked.connect(find)
        save.clicked.connect(save_selected)
        return page

    def open_source(self, record):
        if record and record.get("url"):
            url = QUrl(record["url"])
            if url.isValid() and url.scheme() in {"http", "https"}:
                if not QDesktopServices.openUrl(url):
                    self.status_bar.showMessage("The browser could not open this source.")

    def show_opportunities(self, items):
        self._opportunities = items
        self.opportunity_results.clear()
        for item in items:
            self.opportunity_results.addItem(
                f"{item['title']} - {item['organization']}\n"
                f"{item['details']}\n{item['url']}"
            )

    def progress_page(self):
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h1>Progress Analytics</h1>"))
        refresh = QPushButton("Refresh progress")
        output = QTextEdit()
        output.setReadOnly(True)
        layout.addWidget(refresh)
        canvas = FigureCanvasQTAgg(Figure(figsize=(7, 3), layout="constrained"))
        canvas.setMinimumHeight(190)
        layout.addWidget(canvas)
        layout.addWidget(output)

        def show_progress(result):
            output.setPlainText("\n".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in result.items()))
            canvas.figure.clear()
            axis = canvas.figure.subplots()
            axis.barh(["Roadmaps saved", "Projects completed", "Activities completed", "Portfolio items"],
                      [result["saved_roadmaps"], result["projects_completed"],
                       result["learning_activities_completed"], result["portfolio_total"]])
            axis.set_xlim(left=0)
            canvas.draw_idle()

        refresh.clicked.connect(lambda: self.run_worker(lambda: self.api.get("/progress"), show_progress))
        return page

    def community_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h1>Community Knowledge</h1>"))
        layout.addWidget(text_label("Approved submissions may be shown to users and sent as references for AI guidance. "
                                    "Training is separate and optional. Do not include anyone's private data."))
        title = QLineEdit()
        title.setPlaceholderText("Contribution title")
        category = QLineEdit()
        category.setPlaceholderText("Category")
        source = QLineEdit()
        source.setPlaceholderText("Optional source URL or reference")
        body = QTextEdit()
        body.setPlaceholderText(
            "Share useful educational knowledge. Do not include private or sensitive information."
        )
        training_consent = QCheckBox(
            "I grant future permission to consider this contribution for reviewed training datasets"
        )
        copyright_confirmed = QCheckBox(
            "I own this material or have permission to submit it"
        )
        status = QTextEdit()
        status.setReadOnly(True)
        layout.addWidget(title)
        layout.addWidget(category)
        layout.addWidget(source)
        layout.addWidget(body)
        layout.addWidget(training_consent)
        layout.addWidget(copyright_confirmed)
        submit = QPushButton("Submit for review")
        layout.addWidget(submit)
        def change_permission(item):
            action = "Withdraw" if item["consent_to_training"] else "Grant"
            label = f"{action} future training permission for this specific contribution?"
            if QMessageBox.question(self, "Contribution permission", label) == QMessageBox.StandardButton.Yes:
                self.run_worker(lambda: self.api.put(f"/contributions/{item['id']}/consent", {
                    "consent_enabled": not item["consent_to_training"],
                }), lambda _: self.status_bar.showMessage("Contribution permission updated."))
        add_action(layout, "My submissions and permissions", lambda: self.choose_record(
            "/contributions", "My submissions", "title",
            lambda item: (
                status.setPlainText(f"{item['title']}\nReview: {item['review_status']}\n"
                                    f"Future training permission: {'granted' if item['consent_to_training'] else 'not granted'}"),
                change_permission(item),
            ),
        ))
        layout.addWidget(status)

        def submit_contribution():
            if len(body.toPlainText().strip()) < 20:
                QMessageBox.warning(
                    self,
                    "Community contribution",
                    "The contribution body must contain at least 20 characters.",
                )
                return
            payload = {
                "title": title.text().strip(),
                "category": category.text().strip(),
                "source": source.text().strip() or None,
                "body": body.toPlainText().strip(),
                "consent_to_training": training_consent.isChecked(),
                "copyright_confirmed": copyright_confirmed.isChecked(),
            }
            self.run_worker(
                lambda: self.api.post("/contributions", payload),
                lambda result: status.setPlainText(
                    f"Submitted.\nReview status: {result['review_status']}\n"
                    "This submission is not approved community knowledge or training data."
                ),
            )

        submit.clicked.connect(submit_contribution)
        return page

    def settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h1>Settings</h1>"))
        layout.addWidget(text_label(f"Connected backend: {self.api.base_url}. To change it, sign out first."))
        if self.signed_out:
            add_action(layout, "Sign out", self.logout)
            add_action(layout, "Generate a one-time recovery code", self.recovery_code)
            if self.role == "student":
                add_action(layout, "Delete my account", self.delete_account)
        layout.addWidget(
            QLabel(
                "AI provider credentials are configured only on the backend "
                "and are never exposed to this application."
            )
        )

        layout.addWidget(QLabel("<b>Training permission</b>"))
        self.training_consent = QCheckBox(
            "Allow per-contribution opt-in to future reviewed training drafts"
        )
        layout.addWidget(text_label("Turning this on does not grant permission for past submissions. Turning it off "
                                    "withdraws all contribution training permissions and revokes affected drafts."))
        layout.addWidget(self.training_consent)
        save_consent = QPushButton("Update training permission")
        layout.addWidget(save_consent)
        save_consent.clicked.connect(self.save_training_consent)
        self.run_worker(
            lambda: self.api.get("/training-consent"),
            lambda result: self.training_consent.setChecked(
                result["consent_enabled"]
            ),
        )
        layout.addStretch()
        return page

    def logout(self):
        def on_success(_result):
            self.api.set_token(None)
            if self.signed_out is not None:
                self.signed_out()
            self.close()

        def on_error(message):
            QMessageBox.warning(self, "Signed out locally", "Server-side sign-out was not confirmed.\n" + message)
            on_success(None)

        self.run_worker(lambda: self.api.post("/auth/logout"), on_success, on_error)

    def recovery_code(self):
        password, ok = QInputDialog.getText(self, "Recovery code", "Current password:", QLineEdit.EchoMode.Password)
        if ok:
            self.run_worker(lambda: self.api.post("/auth/recovery-code", {"password": password}),
                            lambda result: QInputDialog.getText(
                                self, "Save your recovery code", "Copy this code to a safe place. It is shown only once:",
                                text=result["recovery_code"],
                            ))

    def delete_account(self):
        confirm = QMessageBox.question(self, "Delete your account?",
                                       "This permanently deletes your account and saved records. Continue?")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        password, ok = QInputDialog.getText(self, "Delete your account", "Current password:", QLineEdit.EchoMode.Password)
        if not ok:
            return
        def on_success(result):
            if result["file_cleanup_pending"]:
                QMessageBox.warning(self, "Account deleted", "Ask the server operator to complete private file cleanup.")
            self.api.set_token(None)
            if self.signed_out is not None:
                self.signed_out()
            self.close()
        self.run_worker(lambda: self.api.post("/auth/delete-account", {"password": password}), on_success)

    def save_training_consent(self):
        payload = {
            "consent_enabled": self.training_consent.isChecked(),
        }
        self.run_worker(
            lambda: self.api.put("/training-consent", payload),
            lambda _: QMessageBox.information(
                self,
                "Training permission",
                "Your future training permission has been updated.",
            ),
        )

    def admin_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h1>Administrator Control Panel</h1>"))

        dashboard = QTextEdit()
        dashboard.setReadOnly(True)
        refresh_dashboard = QPushButton("Refresh dashboard")

        contributions = QListWidget()
        public_title = QLineEdit()
        public_title.setPlaceholderText("Reviewed public title")
        public_body = QTextEdit()
        public_body.setPlaceholderText("Review and remove identifiers from the public text before approving.")
        public_body.setMaximumHeight(120)
        public_source = QLineEdit()
        public_source.setPlaceholderText("Reviewed source reference (optional)")
        submissions = []
        deidentified = QCheckBox("Confirmed de-identified")
        quality = QLineEdit()
        quality.setPlaceholderText("Quality rating from 3 to 5")
        review_notes = QTextEdit()
        review_notes.setPlaceholderText("Optional review notes")
        review_notes.setMaximumHeight(70)
        approve = QPushButton("Approve")
        reject = QPushButton("Reject")

        def refresh():
            def load():
                return self.api.get("/admin/dashboard"), self.api.get("/admin/contributions")
            def show(data):
                metrics, items = data
                dashboard.setPlainText("\n".join(f"{key}: {value}" for key, value in metrics.items()))
                contributions.clear()
                submissions[:] = items
                for item in items:
                    contributions.addItem(f"{item['id']} | {item['review_status']} | {item['title']}")
            self.run_worker(load, show)

        def selected_id():
            row = contributions.currentRow()
            return submissions[row]["id"] if 0 <= row < len(submissions) else None

        def select_submission(row):
            item = submissions[row] if 0 <= row < len(submissions) else {}
            public_title.setText(item.get("title", ""))
            public_body.setPlainText(item.get("body", ""))
            public_source.setText(item.get("source") or "")
            deidentified.setChecked(False)
            quality.clear()
            review_notes.clear()
        contributions.currentRowChanged.connect(select_submission)

        def review(status):
            identifier = selected_id()
            if not identifier:
                QMessageBox.warning(
                    self,
                    "Moderation",
                    "Select a community contribution.",
                )
                return
            try:
                quality_rating = float(quality.text()) if quality.text().strip() else None
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Moderation",
                    "Quality rating must be numeric.",
                )
                return
            payload = {
                "status": status,
                "deidentified": deidentified.isChecked(),
                "quality_rating": quality_rating,
                "notes": review_notes.toPlainText().strip() or None,
            }
            if status == "approved":
                payload.update(public_title=public_title.text().strip(), public_body=public_body.toPlainText().strip(),
                               public_source=public_source.text().strip())
            self.run_worker(
                lambda: self.api.post(
                    f"/admin/contributions/{identifier}/review",
                    payload,
                ),
                lambda _: refresh(),
            )

        approve.clicked.connect(lambda: review("approved"))
        reject.clicked.connect(lambda: review("rejected"))
        refresh_dashboard.clicked.connect(refresh)
        def show_history():
            identifier = selected_id()
            if not identifier:
                self.status_bar.showMessage("Select a contribution.")
                return
            self.run_worker(lambda: self.api.get(f"/admin/contributions/{identifier}/history"),
                            lambda items: dashboard.setPlainText(
                                "\n".join(f"{i['created_at']} | {i['status']} | {i.get('notes') or ''}" for i in items)
                                or "No review history."
                            ))

        def build_draft():
            name, ok = QInputDialog.getText(self, "Prepare a dataset draft", "Version name (no model will be trained):")
            if ok:
                self.run_worker(lambda: self.api.post("/admin/datasets/build", {"name": name}),
                                lambda info: dashboard.setPlainText(
                                    f"Draft {info['name']}: {info['train_count']} training records and "
                                    f"{info['validation_count']} validation records. No model trained."))

        def show_pipeline():
            def load():
                return (self.api.get("/admin/datasets"), self.api.get("/admin/training/history"),
                        self.api.get("/admin/models"))
            def show(groups):
                lines = []
                for title, records in zip(("Datasets", "Audit history", "Model records"), groups, strict=True):
                    lines.extend((title, ""))
                    for record in records:
                        lines.append(f"{record.get('name') or record.get('action')} — {record['status']}")
                        if record.get("evaluation_summary"):
                            lines.append(record["evaluation_summary"])
                    lines.append("")
                dashboard.setPlainText("\n".join(lines))
            self.run_worker(load, show)

        import_button = QPushButton("Import official O*NET ZIP")

        def import_onet():
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Select official O*NET ZIP",
                "",
                "ZIP archives (*.zip)",
            )
            if not path:
                return
            version, ok = QInputDialog.getText(
                self,
                "O*NET version",
                "Database version:",
            )
            if not ok:
                return
            self.run_worker(
                lambda: self.api.upload(
                    "/admin/onet/import",
                    path,
                    {"version": version.strip() or "user-supplied"},
                ),
                lambda result: dashboard.setPlainText(
                    f"O*NET import completed: "
                    f"{result['occupations']} occupations, "
                    f"{result['alternate_titles']} alternate titles, "
                    f"{result['descriptors']} descriptors\n"
                    f"Version: {result['version']} | Skipped rows: {result['skipped_rows']}"
                ),
            )

        import_button.clicked.connect(import_onet)

        layout.addWidget(refresh_dashboard)
        layout.addWidget(dashboard)
        layout.addWidget(QLabel("<b>Community moderation</b>"))
        layout.addWidget(contributions)
        layout.addWidget(public_title)
        layout.addWidget(public_body)
        layout.addWidget(public_source)
        layout.addWidget(deidentified)
        layout.addWidget(quality)
        layout.addWidget(review_notes)
        actions = QHBoxLayout()
        actions.addWidget(approve)
        actions.addWidget(reject)
        add_action(actions, "Review history", show_history)
        layout.addLayout(actions)
        operations = QHBoxLayout()
        operations.addWidget(import_button)
        add_action(operations, "Build reviewed draft", build_draft)
        add_action(operations, "Datasets and model records", show_pipeline)
        layout.addLayout(operations)
        return page


def main(backend_url=None):
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    elif not isinstance(app, QApplication):
        raise RuntimeError("SkillBridge requires a Qt application with GUI support.")
    app.setStyle("Fusion")
    app.setStyleSheet(
        """
        QWidget {
            background: #0b1220;
            color: #edf4ff;
            font-family: "Segoe UI";
            font-size: 10pt;
        }
        #sidebar {
            background: #101a2d;
            min-width: 220px;
            max-width: 220px;
            border-right: 1px solid #26334b;
        }
        #brand {
            color: #63a4ff;
            font-size: 16pt;
            font-weight: bold;
            padding: 18px;
        }
        #nav {
            background: transparent;
            border: none;
            padding: 8px;
        }
        #nav::item {
            padding: 12px;
            border-radius: 8px;
        }
        #nav::item:selected {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #1f67d1, stop:1 #7757d9
            );
        }
        QLineEdit, QTextEdit {
            background: #131d31;
            border: 1px solid #2b3b57;
            border-radius: 8px;
            padding: 8px;
        }
        QListWidget {
            background: #131d31;
            border: 1px solid #2b3b57;
            border-radius: 8px;
            padding: 6px;
        }
        QPushButton {
            background: #1f67d1;
            border: none;
            border-radius: 8px;
            padding: 9px 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: #347fe8;
        }
        QProgressBar {
            background: #131d31;
            border: none;
            max-height: 4px;
        }
        #cardTitle {
            color: #82b4ff;
            font-size: 12pt;
            font-weight: bold;
        }
        """
    )
    try:
        api = ApiClient(backend_url)
    except ApiError as exc:
        QMessageBox.critical(None, "Backend configuration", str(exc))
        return 1
    login = LoginWindow(api)

    def open_main(result):
        window = MainWindow(api, result["role"], signed_out=login.show)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        window.show()
        login.hide()
        login._main_window = window

    login.authenticated = open_main
    login.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
