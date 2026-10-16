"""Running slow work (an AI, a website) without freezing the window."""

from __future__ import annotations

import threading
from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

from bodega.core import errors
from bodega.core.log import get_logger

log = get_logger(__name__)

Job = Callable[[Callable[[int, int], None], threading.Event], object]


class Worker(QThread):
    """Runs job(progress, cancel) in the background. `done` carries what it returned; `failed` a plain
    message. stop() asks it to finish early (the job checks `cancel` between steps)."""

    progress = Signal(int, int)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, job: Job, parent=None, doing: str = "finish that"):
        """`doing`: what a failure says couldn't be done ("open the sheet")."""
        super().__init__(parent)
        self.job = job
        self.doing = doing
        self.cancel = threading.Event()

    def run(self) -> None:
        try:
            result = self.job(lambda n, total: self.progress.emit(n, total), self.cancel)
        except Exception as e:  # plain words: Bodega's own, the computer's translated, or a reference to the log
            self.failed.emit(errors.plain(e, self.doing))
            return
        self.done.emit(result)

    def stop(self) -> None:
        self.cancel.set()
