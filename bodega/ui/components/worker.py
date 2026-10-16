"""Running slow work (an AI, a website) without freezing the window."""

from __future__ import annotations

import threading
import warnings
from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

from bodega.core import errors
from bodega.core.log import get_logger

log = get_logger(__name__)

Job = Callable[[Callable[[int, int], None], threading.Event], object]
_LET_GO: set[QThread] = set()  # threads whose window went while they ran, held until they end


class Background(QThread):
    """Every thread Bodega runs. Qt stops the whole app if a thread is destroyed while it runs, and a window
    takes its threads with it when it goes (Settings closed while it loads the AI's models, say). So when the
    window goes first, the thread is let go of instead: told to stop (`cancel`), kept until it ends, and what it
    says then goes nowhere (SAYS: its signals, disconnected; the window that listened is gone)."""

    SAYS: tuple[str, ...] = ()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cancel = threading.Event()
        if parent is not None:
            parent.destroyed.connect(self._let_go)  # (said while the window still holds it)

    def _let_go(self, *_args) -> None:
        if not self.isRunning():
            return
        self.cancel.set()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # (one with nothing connected says so)
            for name in self.SAYS:
                try:
                    getattr(self, name).disconnect()
                except (RuntimeError, TypeError):
                    pass
        self.setParent(None)
        _LET_GO.add(self)
        self.finished.connect(self._ended)

    def _ended(self) -> None:
        self.wait()  # (finished is said just before it's quite over)
        _LET_GO.discard(self)


class Worker(Background):
    """Runs job(progress, cancel) in the background. `done` carries what it returned; `failed` a plain
    message. stop() asks it to finish early (the job checks `cancel` between steps)."""

    progress = Signal(int, int)
    done = Signal(object)
    failed = Signal(str)
    SAYS = ("progress", "done", "failed")

    def __init__(self, job: Job, parent=None, doing: str = "finish that"):
        """`doing`: what a failure says couldn't be done ("open the sheet")."""
        super().__init__(parent)
        self.job = job
        self.doing = doing

    def run(self) -> None:
        try:
            result = self.job(lambda n, total: self.progress.emit(n, total), self.cancel)
        except Exception as e:  # plain words: Bodega's own, the computer's translated, or a reference to the log
            self.failed.emit(errors.plain(e, self.doing))
            return
        self.done.emit(result)

    def stop(self) -> None:
        self.cancel.set()
