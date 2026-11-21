import logging
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QObject, QThread

from apps.desktop.services.api_client import ApiError


class ApiWorker(QThread):
    def __init__(self, operation: Callable[[], Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.operation = operation
        self.result: Any = None
        self.error: str | None = None

    def run(self) -> None:
        try:
            self.result = self.operation()
        except ApiError as exc:
            self.error = str(exc)
        except OSError:
            self.error = "Could not read the selected local file."
        except Exception:
            logging.getLogger(__name__).exception("Unexpected desktop request failure")
            self.error = "An unexpected request error occurred. See the desktop terminal for details."
