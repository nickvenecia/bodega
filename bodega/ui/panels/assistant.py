"""The AI assistant, as the panel on the right (the same glass as a piece's details): the toolbar's Assistant
button or ⌘J slides it in, and it stays while you work. Click a piece and the panel shows the piece; the button
brings the chat back where you left it, still running whatever job it was doing.

Laid out as the standard's assistant (§14.10, G.25): the header has Clear Chat and ⋯ (Copy Conversation, AI
Settings…) in one capsule, then ✕. Before anything is said, the sparkle and a few suggestions. The conversation
reads as Messages: your words in accent bubbles on the right, the answers as plain words, notices as quiet tinted
notes; under each message (on hover) Copy, and on yours Edit and Ask Again. While it works, "Thinking…" shimmers
and the message field's rim turns in the accent (both still under Reduce Motion). Return sends, Shift-Return starts
a new line; Send sits inside the field and becomes Stop while it works.

A change asked for in the chat waits in a card in the conversation: Decline, or Change N Items (Review… to pick
some); while it waits the field reads "Accept or Decline Above", and after the choice the card says what happened.
The jobs (Update from Links, Find Missing Links, Tidy Up Names, Organize Groups) are buttons; they run in the
background and what they find opens in the Review window. Nothing changes until you say so.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPointF, QRect, QRectF, QSize, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QConicalGradient, QGuiApplication, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from bodega.core import words
from bodega.services.ai.providers import Setup
from bodega.ui.components import access
from bodega.ui.components.panels import SidePanel
from bodega.ui.components.widgets import (
    ElidedLabel,
    add_chip,
    circle_button,
    hbox,
    hint,
    primary_button,
    repolish,
    vbox,
)
from bodega.ui.components.worker import Worker
from bodega.ui.style import theme, tokens

SUGGESTIONS = (  # (icon, words): a click puts them in the message field
    ("tag", "What's all my gear worth?"),
    ("link", "Which pieces have no link?"),
    ("folder", "Put all the Aputure lights in one group"),
)
EXAMPLES = tuple(words_ for _icon, words_ in SUGGESTIONS)
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
PRIVACY = "Your gear list goes to your AI provider, never your renters, and nothing changes until you approve it."


def _quiet(icon: str, tip: str) -> QToolButton:
    """A message's action: a quiet circle, its icon faint until pointed at."""
    b = QToolButton()
    b.setObjectName("MsgAction")
    b.setIcon(theme.icon(icon, theme.FAINT, tokens.MSG_ACTION_ICON))
    b.setIconSize(QSize(tokens.MSG_ACTION_ICON, tokens.MSG_ACTION_ICON))
    b.setFixedSize(tokens.MSG_ACTION, tokens.MSG_ACTION)
    b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


class Message(QWidget):
    """One thing said: `kind` "mine" (an accent bubble on the right), "answer" (plain words on the panel) or
    "note" (a quiet rounded note, `tone` "problem", "done" or "" for news). Always plain text: nothing in an
    answer is formatting. Copy under it on hover; on yours, Edit and Ask Again."""

    edit_wanted = Signal(str)
    again_wanted = Signal(str)

    def __init__(self, kind: str, text: str, tone: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.kind, self.text_ = kind, text
        lay = vbox(self, 0, tokens.SPACE_0_5)
        self.body = QLabel(text)
        self.body.setTextFormat(Qt.TextFormat.PlainText)
        self.body.setWordWrap(True)
        self.body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if kind == "mine":
            self.bubble = QFrame()
            self.bubble.setObjectName("Mine")
            self.body.setObjectName("MineText")
            vbox(self.bubble, (tokens.SPACE_3, tokens.SPACE_2, tokens.SPACE_3, tokens.SPACE_2), 0).addWidget(self.body)
            row = hbox(spacing=0)
            row.addStretch(1)
            row.addWidget(self.bubble)
            lay.addLayout(row)
        elif kind == "note":
            self.bubble = QFrame()
            self.bubble.setObjectName("ChatNote")
            self.bubble.setProperty("tone", tone)
            vbox(self.bubble, (tokens.SPACE_3, tokens.SPACE_2, tokens.SPACE_3, tokens.SPACE_2), 0).addWidget(self.body)
            lay.addWidget(self.bubble)
        else:
            self.bubble = None
            self.body.setObjectName("Answer")
            lay.addWidget(self.body)
        acts = hbox(spacing=tokens.SPACE_0_5)
        if kind == "mine":
            acts.addStretch(1)
        self.copy = _quiet("copy", "Copy")
        self.copy.clicked.connect(self._copy)
        self.actions = [self.copy]
        if kind == "mine":
            self.edit = _quiet("edit", "Edit")
            self.edit.clicked.connect(lambda: self.edit_wanted.emit(self.text_))
            self.again = _quiet("retry", "Ask Again")
            self.again.clicked.connect(lambda: self.again_wanted.emit(self.text_))
            self.actions += [self.edit, self.again]
        for b in self.actions:
            acts.addWidget(b)
            policy = b.sizePolicy()
            policy.setRetainSizeWhenHidden(True)  # (showing them never moves the conversation)
            b.setSizePolicy(policy)
            b.hide()
        if kind != "mine":
            acts.addStretch(1)
        lay.addLayout(acts)
        self.setAccessibleName({"mine": "You", "answer": "Answer", "note": "Note"}[kind])
        self.setAccessibleDescription(text)

    def fit(self, width: int) -> None:
        """A bubble is as wide as its words, and at most BUBBLE_MAX of the conversation's width."""
        if self.kind == "mine":
            room = int(width * tokens.BUBBLE_MAX) - 2 * tokens.SPACE_3
            need = self.body.fontMetrics().boundingRect(
                QRect(0, 0, max(1, room), 1_000_000), int(Qt.TextFlag.TextWordWrap), self.text_
            )
            self.body.setFixedWidth(max(1, min(room, need.width() + 1)))

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self.text_)
        self.copy.setIcon(theme.icon("check", theme.GOOD, tokens.MSG_ACTION_ICON))  # ✓ for a moment
        QTimer.singleShot(
            tokens.COPIED_MS, self, lambda: self.copy.setIcon(theme.icon("copy", theme.FAINT, tokens.MSG_ACTION_ICON))
        )

    def _show_actions(self, on: bool) -> None:
        for b in self.actions:
            b.setVisible(on)

    def enterEvent(self, e):
        self._show_actions(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not any(b.hasFocus() for b in self.actions):
            self._show_actions(False)
        super().leaveEvent(e)


class Thinking(QLabel):
    """ "Thinking…" with light passing across it every SHIMMER_MS (still under Reduce Motion)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Thinking…", parent)
        self.setObjectName("Thinking")
        self._at = 0.0
        self._run = QVariantAnimation(self)
        self._run.setStartValue(0.0)
        self._run.setEndValue(1.0)
        self._run.setDuration(tokens.SHIMMER_MS)
        self._run.setLoopCount(-1)
        self._run.valueChanged.connect(self._step)
        self.hide()

    def _step(self, v) -> None:
        self._at = float(v)
        self.update()

    def set_text(self, text: str) -> None:
        self.setText(text)

    def start(self) -> None:
        self.show()
        if not access.reduce_motion():
            self._run.start()

    def stop(self) -> None:
        self._run.stop()
        self.hide()

    def paintEvent(self, e):
        if self._run.state() != QVariantAnimation.State.Running:
            super().paintEvent(e)
            return
        p = QPainter(self)
        w = self.width()
        x = -w / 2 + self._at * 2 * w  # the light, passing left to right
        g = QLinearGradient(QPointF(x - w / 3, 0), QPointF(x + w / 3, 0))
        g.setColorAt(0, theme.qcolor(tokens.MUTED))
        g.setColorAt(0.5, theme.qcolor(tokens.TEXT))
        g.setColorAt(1, theme.qcolor(tokens.MUTED))
        p.setPen(QPen(g, 1))
        p.setFont(self.font())
        p.drawText(self.rect(), int(self.alignment()), self.text())
        p.end()


class ChangeCard(QFrame):
    """A change asked for in the chat, in the conversation: its title, a line saying how many, what would change
    (old → new, the first few), then Decline and Change N Items sharing its foot. Review… opens them in the
    Review window to pick some. After the choice it says what happened, in its color."""

    SHOWN = 5

    def __init__(self, changes: list, name_of, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ChangeCard")
        lay = vbox(self, (tokens.SPACE_3, tokens.SPACE_3, tokens.SPACE_3, tokens.SPACE_3), tokens.SPACE_2)
        self.title = QLabel("Suggested Changes")
        self.title.setObjectName("ChangeTitle")
        lay.addWidget(self.title)
        pieces = len({c.item_id for c in changes})
        meta = hbox(spacing=tokens.SPACE_2)
        self.meta = hint(f"{words.count(len(changes), 'change')} to {words.count(pieces, 'piece')}")
        meta.addWidget(self.meta, 1)
        self.review = QPushButton("Review…")
        self.review.setObjectName("LinkBtn")
        self.review.setToolTip("Pick which of them to make")
        meta.addWidget(self.review)
        lay.addLayout(meta)
        self.rows = vbox(spacing=tokens.SPACE_1)
        lay.addLayout(self.rows)
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
        self.foot = QWidget()
        fl = hbox(self.foot, 0, tokens.SPACE_2)
        self.decline = QPushButton("Decline")
        self.go = primary_button(f"Change {words.count(pieces, 'Item')}")
        fl.addWidget(self.decline, 1)  # two equal columns
        fl.addWidget(self.go, 1)
        lay.addWidget(self.foot)
        self.outcome = QLabel()
        self.outcome.setObjectName("Outcome")
        self.outcome.hide()
        lay.addWidget(self.outcome)

    def settle(self, text: str, tone: str = "") -> None:
        """The choice is made: the buttons go and the card says what happened."""
        self.foot.hide()
        self.review.hide()
        self.outcome.setText(text)
        self.outcome.setProperty("tone", tone)
        repolish(self.outcome)
        self.outcome.show()


class Composer(QFrame):
    """The message field: a capsule that grows with what's typed, with Send inside it (Stop while it works).
    Return sends; Shift-Return starts a new line. While it works its rim turns in the accent."""

    sent = Signal()
    stop_wanted = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Composer")
        lay = hbox(self, (tokens.SPACE_3, tokens.SPACE_0_5 + 1, tokens.SPACE_0_5 + 1, tokens.SPACE_0_5 + 1), 0)
        self.box = MessageBox(self)
        self.box.sent.connect(self._send)
        self.box.textChanged.connect(self._grow)
        lay.addWidget(self.box, 1, Qt.AlignmentFlag.AlignVCenter)
        self.send = QToolButton()
        self.send.setObjectName("Send")
        self.send.setFixedSize(tokens.SEND_D, tokens.SEND_D)
        self.send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send.clicked.connect(self._pressed)
        lay.addWidget(self.send, 0, Qt.AlignmentFlag.AlignBottom)
        self.working = False
        self._angle = 0.0
        self._rim = QVariantAnimation(self)
        self._rim.setStartValue(0.0)
        self._rim.setEndValue(360.0)
        self._rim.setDuration(tokens.RIM_MS)
        self._rim.setLoopCount(-1)
        self._rim.setEasingCurve(QEasingCurve.Type.Linear)
        self._rim.valueChanged.connect(self._turn)
        self._show_send()
        self._grow()

    def _turn(self, v) -> None:
        self._angle = float(v)
        self.update()

    def _show_send(self) -> None:
        if self.working:
            self.send.setIcon(theme.icon("stop", theme.CARD, tokens.SEND_ICON))
            self.send.setToolTip("Stop")
            self.send.setProperty("stop", True)
        else:
            self.send.setIcon(theme.icon("arrow-up", theme.ON_ACCENT, tokens.SEND_ICON))
            self.send.setToolTip("Send (Return)")
            self.send.setProperty("stop", False)
        self.send.setIconSize(QSize(tokens.SEND_ICON, tokens.SEND_ICON))
        repolish(self.send)

    def set_working(self, on: bool) -> None:
        self.working = on
        self._show_send()
        if on and not access.reduce_motion():
            self._rim.start()
        else:
            self._rim.stop()
        self.update()

    def _pressed(self) -> None:
        if self.working:
            self.stop_wanted.emit()
        else:
            self._send()

    def _send(self) -> None:
        if not self.working:
            self.sent.emit()

    def _grow(self) -> None:
        """28 to 140 tall, with what's typed."""
        doc = self.box.document()
        doc.setTextWidth(self.box.viewport().width())
        h = int(doc.size().height()) + 2 * int(doc.documentMargin())
        self.box.setFixedHeight(max(tokens.COMPOSER_TEXT_MIN, min(tokens.COMPOSER_TEXT_MAX, h)))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._grow()

    def paintEvent(self, e):
        super().paintEvent(e)
        if not self.working:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        g = QConicalGradient(r.center(), -self._angle)  # the rim, turning
        accent, clear = theme.qcolor(tokens.ACCENT), theme.qcolor(tokens.ACCENT)
        clear.setAlpha(40)
        g.setColorAt(0.0, accent)
        g.setColorAt(0.5, clear)
        g.setColorAt(1.0, accent)
        p.setPen(QPen(g, tokens.FOCUS_RING))
        p.setBrush(Qt.BrushStyle.NoBrush)
        radius = min(r.height() / 2, tokens.COMPOSER_MIN_H / 2)
        p.drawRoundedRect(r, radius, radius)
        p.end()


class MessageBox(QPlainTextEdit):
    """The words inside the message field. `text()` / `setText()` as a one-line field has them."""

    sent = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("MessageBox")
        self.setPlaceholderText("Ask Anything")
        self.setTabChangesFocus(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().setDocumentMargin(tokens.SPACE_1)

    def text(self) -> str:
        return self.toPlainText()

    def setText(self, text: str) -> None:
        self.setPlainText(text)
        c = self.textCursor()
        c.movePosition(c.MoveOperation.End)
        self.setTextCursor(c)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.insertPlainText("\n")  # Shift-Return: a new line
            else:
                self.sent.emit()  # Return sends
            return
        super().keyPressEvent(e)


class Conversation(QScrollArea):
    """What's been said, top to bottom, scrolled to the newest. Scrolling it never scrolls the page."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Conversation")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("ConversationBody")
        self.lay = vbox(body, (0, tokens.SPACE_2_5, 0, tokens.SPACE_3), tokens.SPACE_3)
        self.lay.addStretch(1)
        self.setWidget(body)
        self.parts: list[QWidget] = []

    def add(self, w: QWidget) -> None:
        self.lay.addWidget(w)
        self.parts.append(w)
        if isinstance(w, Message):
            w.fit(self.viewport().width())
        QTimer.singleShot(0, self, lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()))

    def remove(self, w: QWidget) -> None:
        if w in self.parts:
            self.parts.remove(w)
            w.hide()
            w.setParent(None)
            w.deleteLater()

    def clear(self) -> None:
        for w in list(self.parts):
            self.remove(w)

    def text(self) -> str:
        """Everything said, as plain text (Copy Conversation)."""
        out = []
        for w in self.parts:
            if isinstance(w, Message):
                who = {"mine": "You", "answer": "Assistant", "note": "Bodega"}[w.kind]
                out.append(f"{who}: {w.text_}")
            elif isinstance(w, ChangeCard):
                said = w.outcome.text() if w.outcome.isVisibleTo(w) else "waiting for an answer"
                out.append(f"Suggested changes: {w.meta.text()} ({said})")
        return "\n\n".join(out)

    def toPlainText(self) -> str:  # (as the old log had it)
        return self.text()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        for w in self.parts:
            if isinstance(w, Message):
                w.fit(self.viewport().width())


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
        self.card: ChangeCard | None = None  # the newest change card
        self._ready = True
        # the header: Clear Chat and ⋯ in one capsule, then ✕ (the standard's G.25)
        self.clear_btn = circle_button("trash", "Clear Chat")
        group = QFrame()
        group.setObjectName("HeadGroup")
        group.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # a capsule around its two circles
        gl = hbox(group, 1, 0)
        actions = self.header.actions
        actions.removeWidget(self.more)
        for b in (self.clear_btn, self.more):
            b.setProperty("grouped", True)
            gl.addWidget(b)
        actions.insertWidget(0, group, 0, Qt.AlignmentFlag.AlignVCenter)
        self.clear_btn.clicked.connect(self.clear_chat)
        self.more.setToolTip("More")
        self.more_menu.addAction(theme.menu_icon("copy"), "Copy Conversation", self.copy_conversation)
        self.more_menu.addAction(theme.menu_icon("cog"), "AI Settings…", self.setup_wanted.emit)
        lay = self.lay
        # before there's an AI to ask: the way to add one
        self.connect_btn = add_chip("Add an API Key")
        self.connect_btn.clicked.connect(self.setup_wanted.emit)
        row = hbox()
        row.addWidget(self.connect_btn)
        row.addStretch(1)
        lay.addLayout(row)

        # before anything is said: the sparkle, then a few suggestions
        self.hello = QWidget()
        hl = vbox(self.hello, (0, tokens.SPACE_5, 0, tokens.SPACE_3), tokens.SPACE_3)
        hl.addStretch(1)
        self.face = QLabel()
        self.face.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(self.face)
        tips = QFrame()
        tips.setObjectName("Suggestions")
        tl = vbox(tips, 0, 0)
        self.examples: list[QPushButton] = []
        for n, (icon, question) in enumerate(SUGGESTIONS):
            b = QPushButton(question)
            b.setObjectName("Suggestion")
            b.setProperty("last", n == len(SUGGESTIONS) - 1)
            b.setIcon(theme.icon(icon, theme.ACCENT, tokens.ICON_SUGGEST))
            b.setIconSize(QSize(tokens.ICON_SUGGEST, tokens.ICON_SUGGEST))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _c=False, q=question: self._suggest(q))
            self.examples.append(b)
            tl.addWidget(b)
        hl.addWidget(tips)
        privacy = hint(PRIVACY)
        privacy.setWordWrap(True)
        privacy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(privacy)
        hl.addStretch(1)
        lay.addWidget(self.hello, 1)
        self.chat = Conversation()
        self.chat.hide()
        lay.addWidget(self.chat, 1)
        self.log = self.chat  # (older name)
        self.thinking = Thinking()

        # a job running: what it's doing, how far, Stop
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

        # jobs, as a block of buttons above the message field
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

        self.composer = Composer()
        self.composer.sent.connect(self._ask)
        self.composer.stop_wanted.connect(self._stop)
        self.question = self.composer.box
        self.question.setAccessibleName("Message")
        self.ask_btn = self.composer.send
        lay.addWidget(self.composer)
        self.recolor()

    def recolor(self) -> None:
        size = tokens.ASSISTANT_FACE
        self.face.setPixmap(theme.icon("assistant", theme.ACCENT, size).pixmap(size, size))
        for (icon, _q), b in zip(SUGGESTIONS, self.examples, strict=True):
            b.setIcon(theme.icon(icon, theme.ACCENT, tokens.ICON_SUGGEST))
        self.composer._show_send()

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
        self.ask_btn.setEnabled(ready and (self.pending is None) and (not self.running() or self.composer.working))
        self.question.setEnabled(ready and self.pending is None)
        for b in self.examples:
            b.setEnabled(ready and self.pending is None)

    def running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def start(self, worker: Worker, what: str, question: bool = False) -> None:
        """Show a job running (the window made the worker and handles what it finds). A question shows
        "Thinking…" in the conversation, with Stop in the message field; a job its own progress row."""
        self.worker = worker
        if question:
            self.chat.add(self.thinking)
            self.thinking.start()
            self.composer.set_working(True)
        else:
            self.busy_text.setText(what)
            self.bar.setRange(0, 0)
            self.busy.show()
        for b in (*self.job_buttons.values(),):
            b.setEnabled(False)
        self.ask_btn.setEnabled(question)  # (it's Stop now)
        worker.progress.connect(self._progress)
        worker.finished.connect(self._finished)
        worker.start()

    def _progress(self, n: int, total: int) -> None:
        self.bar.setRange(0, max(1, total))
        self.bar.setValue(n)

    def _finished(self) -> None:
        self.busy.hide()
        self.thinking.stop()
        if self.thinking in self.chat.parts:
            self.chat.parts.remove(self.thinking)
            self.chat.lay.removeWidget(self.thinking)
        self.composer.set_working(False)
        for b in (*self.job_buttons.values(), self.ask_btn):
            b.setEnabled(self.pending is None and self._ready)

    def _stop(self) -> None:
        if self.worker is not None:
            self.worker.stop()
            self.busy_text.setText("Stopping…")
            self.thinking.set_text("Stopping…")

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
        self.thinking.stop()
        if self.thinking in self.chat.parts:
            self.chat.parts.remove(self.thinking)
            self.chat.lay.removeWidget(self.thinking)
        self.chat.clear()
        self.card = None
        self.chat.hide()
        self.hello.show()

    def copy_conversation(self) -> None:
        QGuiApplication.clipboard().setText(self.chat.text())

    def _waiting(self, on: bool) -> None:
        """While changes wait for an answer, nothing else can be asked."""
        for w in (self.question, self.ask_btn, *self.examples, *self.job_buttons.values()):
            w.setEnabled(not on and self._ready)
        self.question.setPlaceholderText("Accept or Decline Above" if on else "Ask Anything")
        if not on:
            self.question.setFocus()

    def _decide(self, how: str, quiet: bool = False) -> None:
        """The card's answer: "change" all, "decline", or "review" them in the Review window."""
        result, self.pending = self.pending, None
        self._waiting(False)
        if result is None:
            return
        if how == "change":
            self.apply_wanted.emit(list(result.changes))
        elif how == "review":
            self.changes_found.emit(result)
        elif self.card is not None:
            self.card.settle("Declined. Nothing changed.", "")

    def changes_made(self, n: int) -> None:
        """What became of the newest card's changes, on the card (or as a note when there's no card)."""
        text = f"✓ Changed {words.count(n, 'thing')}. A safety copy of how things were is kept."
        if self.card is not None and not self.card.outcome.isVisibleTo(self.card):
            self.card.settle(text, "done")
        else:
            self.say("Bodega", text, "done")

    def nothing_changed(self) -> None:
        if self.card is not None and not self.card.outcome.isVisibleTo(self.card):
            self.card.settle("Nothing changed.", "")
        else:
            self.say("Bodega", "Nothing changed.")

    def _open_chat(self) -> None:
        if self.chat.isHidden():
            self.hello.hide()
            self.chat.show()

    def say(self, who: str, text: str, tone: str = "") -> None:
        """Add to the conversation: "You" a bubble, "AI" an answer, anything else ("Bodega") a note."""
        self._open_chat()
        kind = {"You": "mine", "AI": "answer"}.get(who, "note")
        m = Message(kind, text, tone)
        if kind == "mine":
            m.edit_wanted.connect(self._suggest)
            m.again_wanted.connect(self._again)
        self.chat.add(m)

    def _again(self, question: str) -> None:
        if self.pending is None and not self.running():
            self.question.setText(question)
            self._ask()

    def _ask(self) -> None:
        q = self.question.text().strip()
        if not q or self.ask_job is None or self.running() or self.pending is not None or not self._ready:
            return
        self.say("You", q)
        self.question.setText("")
        job = self.ask_job()  # copies of your gear, made here (not while the job runs)
        w = Worker(lambda _p, _c: job(q), self)
        w.done.connect(self._answered)
        w.failed.connect(lambda e: self.say("Bodega", e, "problem"))
        self.start(w, "Thinking…", question=True)

    def _answered(self, got) -> None:
        reply, result = got
        self.say("AI", reply)
        if result.changes:
            self.pending = result
            self.card = ChangeCard(result.changes, self.name_of)
            self.card.decline.clicked.connect(lambda: self._decide("decline"))
            self.card.go.clicked.connect(lambda: self._decide("change"))
            self.card.review.clicked.connect(lambda: self._decide("review"))
            self.chat.add(self.card)
            self._waiting(True)
            self.card.go.setFocus()
