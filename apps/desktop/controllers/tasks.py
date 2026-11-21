from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from apps.desktop.workers.api_worker import ApiWorker


class TaskRunner(QObject):
    busy_changed = pyqtSignal(bool)
    message = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._workers: list[ApiWorker] = []

    @property
    def active(self) -> int:
        return len(self._workers)

    def is_busy(self) -> bool:
        return bool(self._workers)

    def run(self, operation: Callable[[], Any], on_success: Callable[[Any], object],
            on_error: Callable[[str], object] | None = None) -> None:
        self.busy_changed.emit(True)
        self.message.emit("Working...")
        worker = ApiWorker(operation, self)

        def finished() -> None:
            self._workers.remove(worker)
            if not self._workers:
                self.busy_changed.emit(False)
            worker.deleteLater()
            if worker.error:
                if on_error:
                    on_error(worker.error)
                else:
                    self.message.emit(worker.error)
            else:
                self.message.emit("")
                on_success(worker.result)

        worker.finished.connect(finished)
        self._workers.append(worker)
        worker.start()
