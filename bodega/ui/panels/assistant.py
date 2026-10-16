"""The AI assistant, as the panel on the right (the same glass as a piece's details): the toolbar's Assistant
button or ⌘J slides it in, and it stays while you work. Click a piece and the panel shows the piece; the button
brings the chat back where you left it, still running whatever job it was doing. Its header has Clear Chat, and
the ⋯ has AI Settings.

Ask a question or for a change, or start a job (Update from Links, Find Missing Links, Tidy Up Names, Organize
Groups). A change asked for in the chat waits in a card in the conversation: Decline, or Change N Items (Review…
to pick some). Jobs run in the background and what they find opens in the Review window. Nothing changes until
you say so.
"""

from __future__ import annotations

import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QWidget,
)

from bodega.core import words
from bodega.services.ai.providers import Setup
from bodega.ui.components.panels import SidePanel
from bodega.ui.components.widgets import ElidedLabel, add_chip, hbox, hint, primary_button, vbox
from bodega.ui.components.worker import Worker
from bodega.ui.style import theme, tokens

EXAMPLES = (
    "What's all my gear worth?",
    "Which pieces have no link?",
    "Put the Aputure lights in a group called Aputure",
)
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


class ChangeCard(QFrame):
    """A change asked for in the chat, in the conversation until you answer: what would change (the first few),
    then Decline or Change N Items; Review… opens them in the Review window to pick some."""

    SHOWN = 5

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        lay = vbox(self, tokens.SPACE_3, tokens.SPACE_2)
        self.title = QLabel("Suggested Changes")
        self.title.setObjectName("CardTitle")
        lay.addWidget(self.title)
        self.rows = vbox(spacing=tokens.SPACE_1)
        lay.addLayout(self.rows)
        row = hbox(spacing=tokens.SPACE_2)
        self.review = QPushButton("Review…")
        self.review.setObjectName("LinkBtn")
        self.review.setToolTip("Pick which of them to make")
        row.addWidget(self.review)
        row.addStretch(1)
        self.decline = QPushButton("Decline")
        self.go = primary_button("Change")
        row.addWidget(self.decline)
        row.addWidget(self.go)
        lay.addLayout(row)
        self.hide()

    def show_changes(self, changes: list, name_of) -> None:
        while self.rows.count():
            w = self.rows.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for c in changes[: self.SHOWN]:  # (an AI's words: cleaned before they got here, shown as plain text)
            one = QWidget()
            two = vbox(one, 0, 0)
            name = ElidedLabel(name_of(c.item_id))
            name.setObjectName("ItemTitle")
            what = ElidedLabel(f"{c.label}: {c.old or '—'} → {c.new}")
            what.setObjectName("Meta")
            two.addWidget(name)
            two.addWidget(what)
            self.rows.addWidget(one)
        if len(changes) > self.SHOWN:
            self.rows.addWidget(hint(f"and {len(changes) - self.SHOWN:,} more"))
        pieces = len({c.item_id for c in changes})
        self.go.setText(f"Change {words.count(pieces, 'Item')}")
        self.show()


class AssistantPanel(SidePanel):
    job_wanted = Signal(str)  # "links", "find", "names", "groups": the window gathers the gear and starts it
    setup_wanted = Signal()
    changes_found = Signal(object)  # a request in the chat came back with changes: Review… them
    apply_wanted = Signal(list)  # Change N Items: make these changes

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Assistant", more=True, scroll=False, parent=parent)
        self.worker: Worker | None = None
        self.ask_job = None  # set by the window: () -> (question -> answer)
        self.name_of = lambda item_id: item_id  # set by the window: a piece's name, for the change card
        self.pending = None  # changes asked for in the chat, waiting for an answer in the card
        self.clear_btn = self.header_icon("edit", "Clear Chat")
        self.clear_btn.clicked.connect(self.clear_chat)
        self.more_menu.addAction(theme.menu_icon("cog"), "AI Settings…", self.setup_wanted.emit)
        lay = self.lay
        # before there's an AI to ask: the way to add one
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
        hl.addSpacing(tokens.SPACE_2)
        self.examples: list[QPushButton] = []
        for example in EXAMPLES:  # a few things to ask: a click puts it in the question box
            b = QPushButton(example)
            b.setObjectName("Ghost")
            b.clicked.connect(lambda _c=False, q=example: self._suggest(q))
            self.examples.append(b)
            hl.addWidget(b, 0, Qt.AlignmentFlag.AlignHCenter)
        hl.addStretch(1)
        lay.addWidget(self.hello, 1)
        self.log = QTextBrowser()
        self.log.setOpenLinks(False)  # an answer's links never open from here
        self.log.setObjectName("Notes")
        self.log.hide()
        lay.addWidget(self.log, 1)
        self.card = ChangeCard()
        self.card.decline.clicked.connect(lambda: self._decide("decline"))
        self.card.go.clicked.connect(lambda: self._decide("change"))
        self.card.review.clicked.connect(lambda: self._decide("review"))
        lay.addWidget(self.card)

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
            b.setProperty("tip", tip)
            b.clicked.connect(lambda _c=False, k=key: self.job_wanted.emit(k))
            self.job_buttons[key] = b
            grid.addWidget(b, n // 2, n % 2)
        lay.addLayout(grid)

        row = hbox(spacing=tokens.SPACE_2)
        self.question = QLineEdit()
        self.question.setPlaceholderText("Ask, or ask for a change")
        self.question.setToolTip("Like: put the Aputure lights in a group called Aputure")
        self.question.returnPressed.connect(self._ask)
        self.ask_btn = primary_button("Ask")
        self.ask_btn.clicked.connect(self._ask)
        row.addWidget(self.question, 1)
        row.addWidget(self.ask_btn)
        lay.addLayout(row)
        self.recolor()

    def recolor(self) -> None:
        size = tokens.ASSISTANT_ICON_BIG
        self.face.setPixmap(theme.icon("assistant", theme.ACCENT, size).pixmap(size, size))

    # State
    def show_setup(self, setup: Setup, scope: str) -> None:
        ready = setup.ready()
        self._ready = ready
        self.connect_btn.setVisible(not ready)
        self.scope.setText(scope)
        busy = self.running() or self.pending is not None
        for b in self.job_buttons.values():  # off, it says why
            b.setEnabled(ready and not busy)
            b.setToolTip(
                b.property("tip")
                if ready and not busy
                else "Add an API key first"
                if not ready
                else "Answer the suggested changes first"
                if self.pending is not None
                else "One job at a time"
            )
        self.ask_btn.setEnabled(ready and not busy)
        self.question.setEnabled(ready and self.pending is None)
        for b in self.examples:
            b.setEnabled(ready and self.pending is None)

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
            b.setEnabled(self.pending is None)

    def _stop(self) -> None:
        if self.worker is not None:
            self.worker.stop()
            self.busy_text.setText("Stopping…")

    def shutdown(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(tokens.QUIT_WAIT_MS)

    # Questions
    def _suggest(self, question: str) -> None:
        self.question.setText(question)
        self.question.setFocus()

    def clear_chat(self) -> None:
        """Clear Chat: the conversation goes, the hello comes back (a running job carries on; changes waiting
        for an answer are declined)."""
        if self.pending is not None:
            self._decide("decline", quiet=True)
        self.log.clear()
        self.log.hide()
        self.hello.show()

    def _waiting(self, on: bool) -> None:
        """While changes wait for an answer, nothing else can be asked."""
        for w in (self.question, self.ask_btn, *self.examples, *self.job_buttons.values()):
            w.setEnabled(not on and getattr(self, "_ready", True))
        if not on:
            self.question.setFocus()

    def _decide(self, how: str, quiet: bool = False) -> None:
        """The card's answer: "change" all, "decline", or "review" them in the Review window."""
        result, self.pending = self.pending, None
        self.card.hide()
        self._waiting(False)
        if result is None:
            return
        if how == "change":
            self.apply_wanted.emit(list(result.changes))
        elif how == "review":
            self.changes_found.emit(result)
        elif not quiet:
            self.say("Bodega", "Nothing changed.")

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
            self.pending = result
            self.card.show_changes(result.changes, self.name_of)
            self._waiting(True)
            self.card.go.setFocus()
