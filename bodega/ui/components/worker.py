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

    def __init__(self, job: Job, parent=None):
        super().__init__(parent)
        self.job = job
        self.cancel = threading.Event()

    def run(self) -> None:
        try:
            result = self.job(lambda n, total: self.progress.emit(n, total), self.cancel)
        except OSError as e:  # the plain-words errors (AIError, web, keychain), or the computer's, translated
            self.failed.emit(errors.plain(e, "finish that"))
            return
        except Exception as e:
            self.failed.emit(errors.plain(e, "finish that"))  # with a reference that matches the log
            return
        self.done.emit(result)

    def stop(self) -> None:
        self.cancel.set()
