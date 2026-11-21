from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PyQt6.QtWidgets import QTextEdit, QWidget

from apps.desktop.controllers.session import SessionController
from apps.desktop.controllers.tasks import TaskRunner
from apps.desktop.services.backend import BackendService


@dataclass
class PageContext:
    backend: BackendService
    session: SessionController
    tasks: TaskRunner
    parent: QWidget


class Page(QWidget):
    """A navigable screen; ``title`` is the label shown in the sidebar."""

    title: str = ""

    def __init__(self, context: PageContext) -> None:
        super().__init__()
        self.context = context

    @property
    def backend(self) -> BackendService:
        return self.context.backend

    @property
    def session(self) -> SessionController:
        return self.context.session

    def run(self, operation: Callable[[], Any], on_success: Callable[[Any], object],
            on_error: Callable[[str], object] | None = None) -> None:
        self.context.tasks.run(operation, on_success, on_error)

    def notify(self, text: str) -> None:
        self.context.tasks.message.emit(text)

    def show_in(self, output: QTextEdit) -> Callable[[str], None]:
        """An error handler that writes a readable failure message into an output panel."""
        def handle(message: str) -> None:
            output.setPlainText("This request could not be completed.\n\n" + message)
        return handle
