from collections.abc import Callable
from typing import Any

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from apps.desktop.controllers.session import SessionController
from apps.desktop.controllers.tasks import TaskRunner
from apps.desktop.ui.components.formatting import BASE_NAV_ITEMS
from apps.desktop.ui.pages.admin import AdminPage
from apps.desktop.ui.pages.analytics import ProgressAnalyticsPage
from apps.desktop.ui.pages.base import Page, PageContext
from apps.desktop.ui.pages.career_explorer import CareerExplorerPage
from apps.desktop.ui.pages.community import CommunityPage
from apps.desktop.ui.pages.dashboard import DashboardPage
from apps.desktop.ui.pages.opportunities import OpportunitiesPage
from apps.desktop.ui.pages.portfolio import PortfolioPage
from apps.desktop.ui.pages.profile import ProfilePage
from apps.desktop.ui.pages.projects import ProjectsPage
from apps.desktop.ui.pages.reality_check import RealityCheckPage
from apps.desktop.ui.pages.roadmap import LearningRoadmapPage
from apps.desktop.ui.pages.settings import AccountActions, SettingsPage
from apps.desktop.ui.pages.skill_gap import SkillGapPage

# Page classes keyed by sidebar label; BASE_NAV_ITEMS decides the order they appear in.
PAGE_TYPES: dict[str, type[Page]] = {
    page_type.title: page_type
    for page_type in (
        DashboardPage,
        ProfilePage,
        CareerExplorerPage,
        RealityCheckPage,
        SkillGapPage,
        LearningRoadmapPage,
        PortfolioPage,
        ProjectsPage,
        OpportunitiesPage,
        ProgressAnalyticsPage,
        CommunityPage,
        SettingsPage,
        AdminPage,
    )
}


class MainWindow(QMainWindow):
    """Signed-in shell: sidebar navigation, one stacked page per entry and a shared task runner."""

    def __init__(self, session: SessionController, signed_out: Callable[[], None] | None = None) -> None:
        super().__init__()
        self.session = session
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
        brand = QLabel("SkillBridge AI")
        brand.setObjectName("brand")
        sidebar_layout.addWidget(brand)
        brand_tag = QLabel("CAREER PLATFORM")
        brand_tag.setObjectName("brandTag")
        sidebar_layout.addWidget(brand_tag)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        sidebar_layout.addWidget(self.nav)
        sidebar_layout.addStretch()

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.loading = QProgressBar()
        self.loading.setRange(0, 100)
        self.loading.setValue(100)
        self.loading.setObjectName("loading")
        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack, 1)
        right_layout.addWidget(self.loading)

        layout.addWidget(sidebar)
        layout.addWidget(right, 1)

        # Pages start requests while they are being built, so the runner must be wired up first.
        self.tasks = TaskRunner(self)
        self.tasks.busy_changed.connect(self.set_busy)
        self.tasks.message.connect(self.show_message)

        context = PageContext(backend=session.backend, session=session, tasks=self.tasks, parent=self)
        account = (
            AccountActions(sign_out=self.logout, recovery_code=self.recovery_code, delete_account=self.delete_account)
            if signed_out is not None else None
        )
        titles = [*BASE_NAV_ITEMS, AdminPage.title] if session.is_admin else list(BASE_NAV_ITEMS)
        self.pages: dict[str, Page] = {}
        for title in titles:
            page = self.create_page(title, context, account)
            self.pages[title] = page
            self.nav.addItem(title)
            self.stack.addWidget(self.wrap_scrollable(page))
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

    @staticmethod
    def wrap_scrollable(page: Page) -> QScrollArea:
        """Give every page uniform padding and a scroll bar so tall pages stay usable."""
        inner = page.layout()
        if inner is not None:
            inner.setContentsMargins(24, 20, 24, 20)
            inner.setSpacing(12)
        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        return scroll

    @staticmethod
    def create_page(title: str, context: PageContext, account: AccountActions | None) -> Page:
        page_type = PAGE_TYPES[title]
        if issubclass(page_type, SettingsPage):
            return page_type(context, account)
        return page_type(context)

    def set_busy(self, busy: bool) -> None:
        self.stack.setEnabled(not busy)
        if busy:
            self.loading.setRange(0, 0)
        else:
            self.loading.setRange(0, 100)
            self.loading.setValue(100)

    def show_message(self, text: str) -> None:
        if text:
            self.status_bar.showMessage(text)
        else:
            self.status_bar.clearMessage()

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        if self.tasks.is_busy() and a0 is not None:
            self.status_bar.showMessage("Wait for the current request before closing.")
            a0.ignore()
        else:
            super().closeEvent(a0)

    def finish_sign_out(self) -> None:
        self.session.clear()
        if self.signed_out is not None:
            self.signed_out()
        self.close()

    def logout(self) -> None:
        def on_success(_result: Any) -> None:
            self.finish_sign_out()

        def on_error(message: str) -> None:
            QMessageBox.warning(self, "Signed out locally", "Server-side sign-out was not confirmed.\n" + message)
            on_success(None)

        self.tasks.run(self.session.logout, on_success, on_error)

    def recovery_code(self) -> None:
        password, ok = QInputDialog.getText(self, "Recovery code", "Current password:", QLineEdit.EchoMode.Password)
        if ok:
            self.tasks.run(lambda: self.session.create_recovery_code(password),
                           lambda result: QInputDialog.getText(
                               self, "Save your recovery code",
                               "Copy this code to a safe place. It is shown only once:",
                               text=result["recovery_code"],
                           ))

    def delete_account(self) -> None:
        confirm = QMessageBox.question(self, "Delete your account?",
                                       "This permanently deletes your account and saved records. Continue?")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        password, ok = QInputDialog.getText(self, "Delete your account", "Current password:",
                                            QLineEdit.EchoMode.Password)
        if not ok:
            return

        def on_success(result: dict[str, Any]) -> None:
            if result["file_cleanup_pending"]:
                QMessageBox.warning(self, "Account deleted", "Ask the server operator to complete private file cleanup.")
            self.finish_sign_out()

        self.tasks.run(lambda: self.session.delete_account(password), on_success)
