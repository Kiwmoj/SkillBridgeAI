"""Qt application bootstrap: theme, backend wiring and the login → main window hand-off."""
import sys
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from apps.desktop.config.settings import load_desktop_settings
from apps.desktop.controllers.session import SessionController
from apps.desktop.services.api_client import ApiClient, ApiError
from apps.desktop.services.backend import BackendService
from apps.desktop.ui.styles.theme import apply_theme
from apps.desktop.ui.windows.login_window import LoginWindow
from apps.desktop.ui.windows.main_window import MainWindow


def create_qapplication() -> QApplication:
    """Return the running QApplication, creating one when the process has none yet."""
    app = QApplication.instance()
    if app is None:
        return QApplication(sys.argv)
    if not isinstance(app, QApplication):
        raise RuntimeError("SkillBridge requires a Qt application with GUI support.")
    return app


def run(backend_url: str | None = None) -> int:
    """Start the desktop app against ``backend_url`` (or the configured default) and return the exit code."""
    app = create_qapplication()
    apply_theme(app)
    settings = load_desktop_settings(backend_url)
    try:
        client = ApiClient(settings.backend_url, settings)
    except ApiError as exc:
        QMessageBox.critical(None, "Backend configuration", str(exc))
        return 1
    session = SessionController(BackendService(client))
    login = LoginWindow(session, settings)

    def open_main(_result: dict[str, Any]) -> None:
        window = MainWindow(session, signed_out=login.show)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        window.show()
        login.hide()
        login._main_window = window

    login.authenticated = open_main
    login.show()
    return app.exec()
