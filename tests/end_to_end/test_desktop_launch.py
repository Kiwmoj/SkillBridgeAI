"""Launch the API and the desktop together and drive the real UI over HTTP (offscreen Qt)."""
import os
from time import monotonic
from typing import TypeVar

import pytest

pytest.importorskip("PyQt6")

W = TypeVar("W")


@pytest.fixture
def isolated_launch(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'e2e.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from apps.backend.core import config
    from apps.backend.database import connection

    settings = config.load_settings()
    engine = connection.make_engine(settings.database_url)
    monkeypatch.setattr(config, "settings", settings)
    monkeypatch.setattr(connection, "engine", engine)
    yield
    engine.dispose()


def test_launcher_desktop_registration_navigation_and_logout(isolated_launch):
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication, QPushButton

    from apps.desktop import application
    from apps.desktop.services.api_client import ApiClient
    from apps.desktop.ui.components.formatting import BASE_NAV_ITEMS
    from apps.desktop.ui.pages.dashboard import DashboardPage
    from apps.desktop.ui.windows.login_window import LoginWindow
    from apps.desktop.ui.windows.main_window import MainWindow
    from scripts import launch_local

    stages: list[str] = []
    failures: list[str] = []

    def exercise(url: str) -> int:
        health = ApiClient(url).get("/health")
        assert health["database"] == "healthy" and health["environment"] == "development"
        app = application.create_qapplication()
        deadline = monotonic() + 30
        timer = QTimer()

        def find(kind: type[W]) -> W | None:
            return next((w for w in app.topLevelWidgets() if isinstance(w, kind)), None)

        def step() -> None:
            try:
                assert monotonic() < deadline, f"Timed out after {stages}"
                login, window = find(LoginWindow), find(MainWindow)
                if not stages and login is not None and login.isVisible():
                    login.name_input.setText("E2E Student")
                    login.email_input.setText("e2e@example.com")
                    login.password_input.setText("end-to-end-password")
                    login.register()
                    stages.append("registered")
                elif stages == ["registered"] and window is not None and not window.tasks.is_busy():
                    labels = [item.text() for i in range(window.nav.count()) if (item := window.nav.item(i))]
                    assert labels == list(BASE_NAV_ITEMS), labels
                    dashboard = window.pages["Dashboard"]
                    assert isinstance(dashboard, DashboardPage)
                    assert dashboard.values["Saved roadmaps"].text() == "0"
                    for row in range(window.nav.count()):
                        window.nav.setCurrentRow(row)
                        assert window.stack.currentIndex() == row
                    window.nav.setCurrentRow(labels.index("Progress Analytics"))
                    analytics = window.stack.currentWidget()
                    assert analytics is not None
                    button = next(b for b in analytics.findChildren(QPushButton) if b.text() == "Refresh progress")
                    button.click()
                    stages.append("navigated")
                elif stages[-1:] == ["navigated"] and window is not None and not window.tasks.is_busy():
                    assert not window.status_bar.currentMessage(), window.status_bar.currentMessage()
                    window.logout()
                    stages.append("signed out")
                elif stages[-1:] == ["signed out"] and login is not None and login.isVisible():
                    assert login.session.token is None and login.session.role is None
                    stages.append("done")
                    timer.stop()
                    app.quit()
            except Exception as error:  # noqa: BLE001 - surfaced through the assertion below
                failures.append(repr(error))
                timer.stop()
                app.quit()

        timer.timeout.connect(step)
        timer.start(25)
        return application.run(url)

    original = launch_local.open_desktop
    launch_local.open_desktop = exercise
    try:
        assert launch_local.main() == 0
    finally:
        launch_local.open_desktop = original
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
    assert not failures, failures
    assert stages == ["registered", "navigated", "signed out", "done"]
    assert os.environ["QT_QPA_PLATFORM"] == "offscreen"
