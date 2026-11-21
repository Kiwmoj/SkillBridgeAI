from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QHBoxLayout, QInputDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from apps.desktop.config.settings import DesktopSettings
from apps.desktop.controllers.session import SessionController
from apps.desktop.services.api_client import ApiError
from apps.desktop.ui.components.widgets import add_action, text_label
from apps.desktop.workers.api_worker import ApiWorker

if TYPE_CHECKING:
    from apps.desktop.ui.windows.main_window import MainWindow


class LoginWindow(QWidget):
    """Sign-in, registration and recovery-code password reset against the configured backend."""

    def __init__(self, session: SessionController, settings: DesktopSettings) -> None:
        super().__init__()
        self.session = session
        self.settings = settings
        self.authenticated: Callable[[dict[str, Any]], None] | None = None
        self._main_window: MainWindow | None = None
        self._worker: ApiWorker | None = None
        self.setWindowTitle(settings.app_name)
        self.resize(460, 360)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "<h1>SkillBridge AI</h1>"
                "<p>Career development for every occupation</p>"
            )
        )
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Full name")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.server_input = QLineEdit(session.backend.base_url)
        self.server_input.setPlaceholderText("Backend URL")
        layout.addWidget(text_label("Backend address"))
        layout.addWidget(self.server_input)
        layout.addWidget(self.name_input)
        layout.addWidget(self.email_input)
        layout.addWidget(self.password_input)

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

    def login(self) -> None:
        email, password = self.email_input.text().strip(), self.password_input.text()
        self.run_request(lambda: self.session.login(email, password), self.finish_auth, "Signing in...")

    def register(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            self.status.setText("Enter your name to create an account.")
            return
        email, password = self.email_input.text().strip(), self.password_input.text()
        self.run_request(lambda: self.session.register(name, email, password), self.finish_auth,
                         "Creating account...")

    def run_request(self, operation: Callable[[], Any], on_success: Callable[[Any], object], status: str) -> None:
        if self._worker is not None:
            return
        try:
            self.session.set_backend_url(self.server_input.text())
        except ApiError as exc:
            self.status.setText(str(exc))
            return
        self.status.setText(status)
        self.setEnabled(False)
        worker = ApiWorker(operation, self)
        self._worker = worker

        def finished() -> None:
            self._worker = None
            self.setEnabled(True)
            worker.deleteLater()
            if worker.error:
                self.status.setText(worker.error)
            else:
                on_success(worker.result)

        worker.finished.connect(finished)
        worker.start()

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        if self._worker is not None and a0 is not None:
            a0.ignore()
        else:
            super().closeEvent(a0)

    def reset_password(self) -> None:
        email = self.email_input.text().strip()
        if not email:
            self.status.setText("Enter your account email first.")
            return
        code, ok = QInputDialog.getText(self, "Password recovery", "Saved one-time recovery code:")
        if not ok:
            return
        password, ok = QInputDialog.getText(self, "Password recovery", "New password:", QLineEdit.EchoMode.Password)
        if ok:
            self.run_request(lambda: self.session.reset_password(email, code, password),
                             lambda _: self.status.setText("Password reset. You can sign in now."),
                             "Resetting password...")

    def finish_auth(self, result: dict[str, Any]) -> None:
        self.session.apply(result)
        self.password_input.clear()
        self.status.clear()
        if callable(self.authenticated):
            self.authenticated(result)
