"""The AI assistant, as the panel on the right (the same glass as a piece's details): the toolbar's speech bubble
or ⌘J slides it in, and it stays while you work. Click a piece and the panel shows the piece; the bubble brings
the chat back where you left it, still running whatever job it was doing.

Ask a question or for a change, or start a job (Update from Links, Find Missing Links, Tidy Up Names, Organize
Groups). Jobs run in the background; what they find opens in the Review window, and nothing changes until you
approve it there.
"""

from __future__ import annotations

import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QWidget,
)

from bodega.services.ai.providers import Setup
from bodega.ui.components.panels import SidePanel
from bodega.ui.components.widgets import add_chip, hbox, hint, vbox
from bodega.ui.components.worker import Worker
from bodega.ui.style import theme, tokens

JOBS = [
    (
        "links",
        "Update from Links",
        "Prices and names from each piece's link",
    ),
    ("find", "Find Missing Links", "Product pages for gear without a link, each one checked"),
    ("names", "Tidy Up Names", "Names like the maker writes them, with Company and Series"),
    ("groups", "Organize Groups", "Gear sorted into clear groups, with new ones where needed"),
]


class AssistantPanel(SidePanel):
    job_wanted = Signal(str)  # "links", "find", "names", "groups": the window gathers the gear and starts it
    setup_wanted = Signal()
    changes_found = Signal(object)  # a request in the chat came back with changes: review them

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Assistant", scroll=False, parent=parent)
        self.worker: Worker | None = None
        self.ask_job = None  # set by the window: () -> (question -> answer)
        self.header_icon("cog", "AI Settings").clicked.connect(self.setup_wanted.emit)
        lay = self.lay
        # which AI it is (or, before there is one, the button to connect one)
        self.who = hint("")
        lay.addWidget(self.who)
        self.connect_btn = add_chip("Add an API Key")
        self.connect_btn.clicked.connect(self.setup_wanted.emit)
        row = hbox()
        row.addWidget(self.connect_btn)
        row.addStretch(1)
        lay.addLayout(row)

        # the conversation (before the first message: a hello)
        self.hello = QWidget()
        hl = vbox(self.hello, (0, tokens.SPACE_5, 0, tokens.SPACE_5), tokens.SPACE_2)
        hl.addStretch(1)
        self.face = QLabel()
        self.face.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hi = QLabel("Ask About Your Gear")
        hi.setObjectName("EmptyTitle")
        hi.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = hint(
            "Ask a question, or ask for a change. Your gear list goes to your AI provider, never your renters, "
            "and nothing changes until you approve it."
        )
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for w in (self.face, hi, sub):
            hl.addWidget(w)
        hl.addStretch(1)
        lay.addWidget(self.hello, 1)
        self.log = QTextBrowser()
        self.log.setOpenLinks(False)  # an answer's links never open from here
        self.log.setObjectName("Notes")
        self.log.hide()
        lay.addWidget(self.log, 1)

        self.busy = QWidget()
        bl = hbox(self.busy, 0, tokens.SPACE_2)
        self.busy_text = hint("")
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(tokens.TRACK_H)
        self.stop = QPushButton("Stop")
        self.stop.clicked.connect(self._stop)
        bl.addWidget(self.busy_text)
        bl.addWidget(self.bar, 1)
        bl.addWidget(self.stop)
        self.busy.hide()
        lay.addWidget(self.busy)

        # jobs, as a block of buttons above the question
        self.scope = hint("")
        lay.addWidget(self.scope)
        grid = QGridLayout()
        grid.setSpacing(tokens.SPACE_2)
        self.job_buttons: dict[str, QPushButton] = {}
        for n, (key, label, tip) in enumerate(JOBS):
            b = QPushButton(label)
            b.setToolTip(tip)
            b.clicked.connect(lambda _c=False, k=key: self.job_wanted.emit(k))
            self.job_buttons[key] = b
            grid.addWidget(b, n // 2, n % 2)
        lay.addLayout(grid)

        row = hbox(spacing=tokens.SPACE_2)
        self.question = QLineEdit()
        self.question.setPlaceholderText("Ask, or ask for a change")
        self.question.setToolTip("Like: put the Aputure lights in a group called Aputure")
        self.question.returnPressed.connect(self._ask)
        self.ask_btn = QPushButton("Ask")
        self.ask_btn.setObjectName("Primary")
        self.ask_btn.clicked.connect(self._ask)
        row.addWidget(self.question, 1)
        row.addWidget(self.ask_btn)
        lay.addLayout(row)
        self.recolor()

    def recolor(self) -> None:
        size = tokens.ASSISTANT_ICON_BIG
        self.face.setPixmap(theme.icon("assistant", theme.ACCENT, size).pixmap(size, size))

    # ------------------------------------------------------------------ state
    def show_setup(self, setup: Setup, scope: str) -> None:
        ready = setup.ready()
        p = setup.p
        self.who.setText(f"{p.label} · {setup.model}" if ready and p else "")
        self.who.setVisible(ready)
        self.connect_btn.setVisible(not ready)
        self.scope.setText(scope)
        for b in self.job_buttons.values():
            b.setEnabled(ready and not self.running())
        self.ask_btn.setEnabled(ready and not self.running())
        self.question.setEnabled(ready)

    def running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def start(self, worker: Worker, what: str) -> None:
        """Show a job running (the window made the worker and handles what it finds)."""
        self.worker = worker
        self.busy_text.setText(what)
        self.bar.setRange(0, 0)
        self.busy.show()
        for b in (*self.job_buttons.values(), self.ask_btn):
            b.setEnabled(False)
        worker.progress.connect(self._progress)
        worker.finished.connect(self._finished)
        worker.start()

    def _progress(self, n: int, total: int) -> None:
        self.bar.setRange(0, max(1, total))
        self.bar.setValue(n)

    def _finished(self) -> None:
        self.busy.hide()
        for b in (*self.job_buttons.values(), self.ask_btn):
            b.setEnabled(True)

    def _stop(self) -> None:
        if self.worker is not None:
            self.worker.stop()
            self.busy_text.setText("Stopping…")

    def shutdown(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(tokens.QUIT_WAIT_MS)

    # ------------------------------------------------------------------ questions
    def say(self, who: str, text: str) -> None:
        """Add a line to the conversation (always as plain text: nothing in an answer is formatting)."""
        if self.log.isHidden():
            self.hello.hide()
            self.log.show()
        self.log.append(f"<p><b>{html.escape(who)}</b><br>{html.escape(text).replace(chr(10), '<br>')}</p>")

    def _ask(self) -> None:
        q = self.question.text().strip()
        if not q or self.ask_job is None or self.running():
            return
        self.say("You", q)
        self.question.clear()
        job = self.ask_job()  # copies of your gear, made here (not while the job runs)
        w = Worker(lambda _p, _c: job(q), self)
        w.done.connect(self._answered)
        w.failed.connect(lambda e: self.say("Bodega", e))
        self.start(w, "Thinking…")

    def _answered(self, got) -> None:
        reply, result = got
        self.say("AI", reply)
        if result.changes:
            n = len(result.changes)
            self.say("Bodega", f"{n} change{'s' if n != 1 else ''} to review.")
            self.changes_found.emit(result)
