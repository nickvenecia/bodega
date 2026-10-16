"""Small reusable widgets."""

from __future__ import annotations

import math
import re

from PySide6.QtCore import (
    QDate,
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QCursor, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractSpinBox,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyledItemDelegate,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from bodega.core.model import MAX_QTY
from bodega.ui.components import access, glass
from bodega.ui.style import theme, tokens


def section_label(text: str) -> QLabel:
    """The small Title Case label above a group of controls."""
    lbl = QLabel(text)
    lbl.setObjectName("SectionLabel")
    return lbl


def hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Hint")
    lbl.setWordWrap(True)
    return lbl


def vbox(
    widget: QWidget | None = None,
    margins: int | tuple[int, int, int, int] = 0,
    spacing: int = tokens.SPACE_2,
) -> QVBoxLayout:
    """A vertical layout using the spacing tokens (never type raw numbers in layouts)."""
    lay = QVBoxLayout(widget) if widget is not None else QVBoxLayout()
    m = (margins,) * 4 if isinstance(margins, int) else margins
    lay.setContentsMargins(*m)
    lay.setSpacing(spacing)
    return lay


def hbox(
    widget: QWidget | None = None,
    margins: int | tuple[int, int, int, int] = 0,
    spacing: int = tokens.SPACE_2,
) -> QHBoxLayout:
    """A horizontal layout using the spacing tokens."""
    lay = QHBoxLayout(widget) if widget is not None else QHBoxLayout()
    m = (margins,) * 4 if isinstance(margins, int) else margins
    lay.setContentsMargins(*m)
    lay.setSpacing(spacing)
    return lay


class Section(QWidget):
    """A labelled group: a small Title Case label, then its controls SPACE_1 below it.

    Put Sections in a layout with spacing SPACE_3 and every panel lines up the same way.
    Hiding a Section hides its label and controls together (and the gap collapses).
    """

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.lay = vbox(self, 0, tokens.SPACE_1)
        self.label = section_label(title)
        self.label.setVisible(bool(title))
        self.lay.addWidget(self.label)

    def add(self, item: QWidget | QHBoxLayout | QVBoxLayout) -> None:
        if isinstance(item, QWidget):
            self.lay.addWidget(item)
            self._name(item)
        else:
            self.lay.addLayout(item)
            for i in range(item.count()):
                w = item.itemAt(i).widget()
                if w is not None:
                    self._name(w)

    def _name(self, w: QWidget) -> None:
        """A field is known by its label (a screen reader says "Company, text field", not just "text field")."""
        title = self.label.text().replace("&&", "&")
        if title and isinstance(w, (QLineEdit, QComboBox, QPlainTextEdit, QAbstractSpinBox)) and not w.accessibleName():
            w.setAccessibleName(title)
            self.label.setBuddy(w)

    def set_title(self, title: str) -> None:
        self.label.setText(title)
        self.label.setVisible(bool(title))


class ElidedLabel(QLabel):
    """A one-line label that cuts long text short with "…" instead of widening its panel. The whole text stays
    its tooltip (when it's cut) and its name for screen readers. `mode`: ElideRight for names and words,
    ElideMiddle for a file's path (its start and its name both matter)."""

    def __init__(self, text: str = "", parent: QWidget | None = None, mode=Qt.TextElideMode.ElideRight):
        super().__init__(parent)
        self._full = ""
        self._mode = mode
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.set_full_text(text)

    def set_full_text(self, text: str) -> None:
        self._full = text
        self.setToolTip("")
        self.setAccessibleName(text)  # read out whole, never "Sony FX6 Cinema…"
        self._elide()

    def full_text(self) -> str:
        return self._full

    def _elide(self) -> None:
        shown = self.fontMetrics().elidedText(self._full, self._mode, max(1, self.width()))
        self.setText(shown)
        self.setToolTip(theme.plain_tip(self._full) if shown != self._full else "")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._elide()

    def sizeHint(self) -> QSize:  # as wide as the whole text, when there's room
        return QSize(self.fontMetrics().horizontalAdvance(self._full) + tokens.TEXT_SLACK, super().sizeHint().height())

    def minimumSizeHint(self) -> QSize:  # …but it gives way to everything else first
        return QSize(0, super().minimumSizeHint().height())


class _FoldHeader(QPushButton):
    """The Disclosure's header: its text is cut short with "…" rather than widening the panel."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._full = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    def set_full_text(self, text: str) -> None:
        self._full = text
        self.setAccessibleName(text.replace("&&", "&").strip())  # whole, even when it's shown cut short
        self._elide()

    def _elide(self) -> None:
        room = self.width() - self.iconSize().width() - tokens.SPACE_3
        self.setText(self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, max(1, room)))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._elide()


class Card(QFrame):
    """A titled group in an inspector panel: a soft tinted card (the look every panel's groups share).
    Gear's parts, a kit's and a rental's fold-away groups are all Cards."""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.outer = vbox(self, tokens.SPACE_3, tokens.SPACE_2)
        self.head = hbox(spacing=tokens.SPACE_2)
        self.title = QLabel(title)
        self.title.setObjectName("CardTitle")
        self.title.setVisible(bool(title))
        self.head.addWidget(self.title, 1)
        self.outer.addLayout(self.head)
        self.lay = vbox(spacing=tokens.SPACE_2)
        self.outer.addLayout(self.lay)

    def add(self, item: QWidget | QHBoxLayout | QVBoxLayout) -> None:
        if isinstance(item, QWidget):
            self.lay.addWidget(item)
        else:
            self.lay.addLayout(item)


class Disclosure(QFrame):
    """A fold-away group: a header row that opens and closes the controls under it.

    Folded, the header says what's inside ("Line Items · 3 items · $2,700.00"), so nothing that changes
    the page is ever hidden silently. (`first` is kept for callers; every group is now its own card.)"""

    toggled = Signal(bool)

    def __init__(self, title: str, is_open: bool = False, first: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._title = title
        self._summary = ""
        self.setObjectName("Card")  # looks like every other group in a panel
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer = vbox(self, tokens.SPACE_3, tokens.SPACE_2)
        self.header = _FoldHeader()
        self.header.setObjectName("Disclosure")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.clicked.connect(lambda: self.set_open(not self.body.isVisibleTo(self), emit=True))
        outer.addWidget(self.header)
        self.body = QWidget()
        self.lay = vbox(self.body, 0, tokens.SPACE_2)
        outer.addWidget(self.body)
        self.set_open(is_open)

    def add(self, item: QWidget | QHBoxLayout | QVBoxLayout) -> None:
        if isinstance(item, QWidget):
            self.lay.addWidget(item)
        else:
            self.lay.addLayout(item)

    def is_open(self) -> bool:
        return self.body.isVisibleTo(self)

    def set_open(self, on: bool, emit: bool = False) -> None:
        self.body.setVisible(on)
        self.header.setIcon(theme.icon("chevron" if on else "chevron-right", theme.MUTED))
        self.header.setToolTip("Hide" if on else "Show")
        self.header.setProperty("named_by_hand", True)
        self.header.setAccessibleName(self._title.replace("&&", "&"))
        self.header.setAccessibleDescription("Expanded" if on else "Collapsed")  # its state, said aloud
        self._show_title()
        if emit:
            self.toggled.emit(on)

    def set_summary(self, text: str) -> None:
        self._summary = text.replace("&", "&&")  # a lone & would underline the next letter instead
        self._show_title()

    def _show_title(self) -> None:
        folded = not self.body.isVisibleTo(self)
        self.header.set_full_text(f" {self._title}" + (f"  ·  {self._summary}" if folded and self._summary else ""))


def announce(w: QWidget, text: str) -> None:
    """Say `text` to a screen reader now (a toast, a status line), without moving the focus."""
    from PySide6.QtGui import QAccessible

    try:
        from PySide6.QtGui import QAccessibleAnnouncementEvent

        QAccessible.updateAccessibility(QAccessibleAnnouncementEvent(w, text))
    except (ImportError, RuntimeError, TypeError):  # an older Qt, or no screen reader to tell
        pass


class StatusLabel(QLabel):
    """A status line (Checking…, a clash under a field, how far a check-out has got): a screen reader hears
    each new message as it appears, without the focus moving."""

    def setText(self, text: str) -> None:
        changed = text != self.text()
        super().setText(text)
        if changed and text and self.isVisible():
            announce(self, text)


def status_line(text: str = "", hinted: bool = True) -> StatusLabel:
    """A StatusLabel: in the hint's look (`hinted`), or plain for its own object name."""
    lbl = StatusLabel(text)
    if hinted:
        lbl.setObjectName("Hint")
    lbl.setWordWrap(True)
    return lbl


def one_stop(text: str) -> str:
    """A sentence that ends in a name with its own full stop ("Saved Northwind Inc..") ends with one."""
    return text[:-1] if text.endswith("..") and not text.endswith("...") else text


def repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


def rows_done(layout: QLayout) -> None:
    """A list of rows (each an "ItemBox") is built, or searched: the last one shown has no hairline under it."""
    rows = [layout.itemAt(n).widget() for n in range(layout.count())]
    rows = [w for w in rows if w is not None and w.objectName() == "ItemBox" and not w.isHidden()]
    for w in rows:
        if w.property("last") != (w is rows[-1]):
            w.setProperty("last", w is rows[-1])
            repolish(w)


class AccentPicker(QWidget):
    """A row of color circles (tokens.ACCENTS), the chosen one ringed. Click, or the arrow keys."""

    picked = Signal(str)

    def __init__(self, current: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.keys = list(tokens.ACCENTS)
        self.current = current if current in tokens.ACCENTS else tokens.APP_ACCENT
        self._hover = ""
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(tokens.CONTROL_H)
        self.setMinimumWidth(self._pitch() * len(self.keys))
        self.setAccessibleName("Accent Color")
        self._say()

    def _say(self) -> None:
        """The chosen color, for screen readers ("Blue")."""
        self.setAccessibleDescription(tokens.ACCENTS[self.current][0])

    @staticmethod
    def _pitch() -> int:
        return tokens.SWATCH + 2 * tokens.SWATCH_RING * 2 + tokens.SPACE_1

    def _rect(self, i: int) -> QRectF:
        outer = tokens.SWATCH + 4 * tokens.SWATCH_RING
        y = (self.height() - outer) / 2
        return QRectF(i * self._pitch(), y, outer, outer)

    def _key_at(self, pos) -> str:
        for i, k in enumerate(self.keys):
            if self._rect(i).contains(pos):
                return k
        return ""

    def set_value(self, key: str) -> None:
        self.current = key if key in tokens.ACCENTS else tokens.APP_ACCENT
        self._say()
        self.update()

    def _pick(self, key: str) -> None:
        if key and key != self.current:
            self.current = key
            self._say()
            self.update()
            self.picked.emit(key)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ring = tokens.SWATCH_RING
        for i, k in enumerate(self.keys):
            r = self._rect(i)
            dot = r.adjusted(2 * ring, 2 * ring, -2 * ring, -2 * ring)
            if k == self.current or k == self._hover:
                pen = QPen(theme.qcolor(tokens.TEXT if k == self.current else tokens.BORDER_HOVER))
                pen.setWidthF(ring)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(r.adjusted(ring / 2, ring / 2, -ring / 2, -ring / 2))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(theme.qcolor(tokens.accent_of(k)))
            p.drawEllipse(dot)
        if self.hasFocus():  # the keyboard is here: the standard's 2-point ring
            pen = QPen(theme.qcolor(tokens.ACCENT))
            pen.setWidthF(tokens.FOCUS_RING)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(self._rect(self.keys.index(self.current)))

    def mouseMoveEvent(self, e) -> None:
        k = self._key_at(e.position())
        if k != self._hover:
            self._hover = k
            self.update()
        name = tokens.ACCENTS[k][0] if k else ""
        if k == tokens.APP_ACCENT:
            name += " (Bodega's own)"
        self.setToolTip(name)

    def leaveEvent(self, _e) -> None:
        self._hover = ""
        self.update()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._pick(self._key_at(e.position()))

    def keyPressEvent(self, e) -> None:
        step = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1}.get(e.key())
        if step is None:
            super().keyPressEvent(e)
            return
        i = (self.keys.index(self.current) + step) % len(self.keys)
        self._pick(self.keys[i])


class Segmented(QFrame):
    """A row of mutually exclusive buttons. The highlight under the choice slides to the new one (it jumps
    with Reduce Motion)."""

    changed = Signal(str)

    def __init__(self, items: list[tuple[str, str]], compact: bool = False, parent: QWidget | None = None):
        """`compact`: each button as wide as its word, instead of sharing the full width."""
        super().__init__(parent)
        self.setObjectName("Seg")
        self.setFixedHeight(tokens.CONTROL_H)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(*(tokens.SEG_INSET,) * 4)
        lay.setSpacing(tokens.SEG_INSET)
        self.thumb = QFrame(self)  # the highlight, under the buttons
        self.thumb.setObjectName("SegThumb")
        self.thumb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.thumb.hide()
        self._slide = QVariantAnimation(self)
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide.valueChanged.connect(self.thumb.setGeometry)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.group.buttonToggled.connect(lambda _b, on: on and self._move(animate=self.isVisible()))
        self.buttons: dict[str, QPushButton] = {}
        for key, label in items:
            b = QPushButton(label)
            b.setObjectName("SegBtn")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(
                QSizePolicy.Policy.Preferred if compact else QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            self.group.addButton(b)
            lay.addWidget(b)
            self.buttons[key] = b
        widest = max((b.sizeHint().width() for b in self.buttons.values()), default=0)
        for b in self.buttons.values():  # every segment as wide as the widest (Apple's segmented controls)
            b.setMinimumWidth(widest)

    def set_value(self, key: str) -> None:
        if key in self.buttons:
            self.buttons[key].setChecked(True)

    def _move(self, animate: bool) -> None:
        """The highlight to the picked button: sliding there, or straight there."""
        b = self.group.checkedButton()
        if b is None:
            self.thumb.hide()
            return
        ms = access.duration(tokens.SEG_SLIDE_MS) if animate and self.thumb.isVisible() else 0
        self._slide.stop()
        if ms:
            self._slide.setDuration(ms)
            self._slide.setStartValue(self.thumb.geometry())
            self._slide.setEndValue(b.geometry())
            self._slide.start()
        else:
            self.thumb.setGeometry(b.geometry())
        self.thumb.show()
        self.thumb.lower()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._move(animate=False)

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self, lambda: self._move(animate=False))

    def value(self) -> str:
        for k, b in self.buttons.items():
            if b.isChecked():
                return k
        return ""


class Banner(QFrame):
    """A problem that lasts, across the top of the page: what's wrong and what to do, one action, and ✕ to
    put it away. Put away, it comes back the next time the problem happens (standard §4.10)."""

    acted = Signal()

    def __init__(self, action: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Banner")
        lay = hbox(self, (tokens.SPACE_3, tokens.SPACE_2, tokens.SPACE_2, tokens.SPACE_2), tokens.SPACE_2)
        self.icon = QLabel()
        self.icon.setPixmap(theme.icon("alert", tokens.WARN).pixmap(tokens.ICON, tokens.ICON))
        lay.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        self.text = QLabel()
        self.text.setWordWrap(True)
        lay.addWidget(self.text, 1)
        self.button = QPushButton(action)
        self.button.clicked.connect(self.acted)
        lay.addWidget(self.button)
        self.close_btn = icon_button("x", "Hide this until it happens again")
        self.close_btn.setAccessibleName("Hide")
        self.close_btn.clicked.connect(self.hide)
        lay.addWidget(self.close_btn)
        self.hide()

    def say(self, text: str) -> None:
        self.text.setText(text)
        self.show()


class TickMenu(QMenu):
    """A menu of ticks that stays open while several change (the standard's 4.2, as the Finder's View Options):
    a click or Return on a tickable choice ticks it and leaves the menu up; anything else closes it as usual."""

    def _keeps_open(self, a) -> bool:
        return a is not None and a.isCheckable() and a.isEnabled() and not a.menu()

    def mouseReleaseEvent(self, e) -> None:
        a = self.actionAt(e.position().toPoint())
        if self._keeps_open(a):
            a.trigger()
            return
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e) -> None:
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space) and self._keeps_open(self.activeAction()):
            self.activeAction().trigger()
            return
        super().keyPressEvent(e)


class Toast(QWidget):
    """A short message floating over the bottom of the page: it rises and fades in, waits, and fades away.
    Its tone's icon says what kind it is: "done" (a green check), "problem" (an amber alert, on an amber-tinted
    toast) or news (an info sign). It never takes a click (what's under it still works); resting the pointer on
    it keeps it up while you read. Painted, so its words are always plain text.
    "error" is a problem that needs you (a file that couldn't be read, a photo that couldn't be used): it looks
    like a problem, with a ✕, and stays until it's clicked away or another message takes its place.
    show_job() is slow work under way: its words, a bar when how much is known (a spinner while it isn't), and
    Stop; it stays until the job's own last message takes its place.
    `action` ("Undo", undo): a capsule after its words that does it ("Deleted Sony FX6. Undo"); such a toast stays
    TOAST_UNDO_MS, and longer while the pointer rests on it (the standard's 4.19: ⌘Z does the same).
    `anchor`: where it centres itself, in the parent's coordinates (the page, between the side panels)."""

    TONES = {
        "done": ("check", "TOAST_DONE"),
        "problem": ("alert", "TOAST_PROBLEM"),
        "error": ("alert", "TOAST_PROBLEM"),
        "job": ("", "TOAST_TEXT"),
        "": ("info", "TOAST_TEXT"),
    }

    def __init__(self, parent: QWidget, anchor=None):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.anchor = anchor or parent.rect
        self.text, self.tone = "", ""
        self._ms = tokens.TOAST_MS
        self._shown = 0.0  # 0 gone … 1 all the way in
        self._leaving = False
        self._pill = QRectF()
        self._anim = QVariantAnimation(self)
        self._anim.valueChanged.connect(self._step)
        self._anim.finished.connect(self._settled)
        self._t = QTimer(self)
        self._t.setSingleShot(True)
        self._t.timeout.connect(self._time_up)
        self._action = None  # its capsule's job: a job's Stop, a delete's Undo
        self._action_word = ""
        self._frac: float | None = None  # how far a job is (None: not known, so a spinner)
        self._action_rect = QRectF()
        self._turn = QVariantAnimation(self)  # the spinner
        self._turn.setStartValue(0.0)
        self._turn.setEndValue(360.0)
        self._turn.setLoopCount(-1)
        self._turn.valueChanged.connect(lambda _v: self.update())
        self.hide()

    def show_job(self, text: str, done: int = 0, total: int = 0, stop=None) -> None:
        """Slow work under way ("Backing up: 120 of 800 files"). `total` known: a bar; not: a spinner. `stop`:
        what Stop does (none: no Stop)."""
        self._frac = min(1.0, max(0.0, done / total)) if total > 0 else None
        self.show_message(text, "job", action=("Stop", stop) if stop is not None else None)

    def show_message(self, text: str, tone: str = "", ms: int = 0, action=None) -> None:
        """`ms`: how long it stays (0: news and done 3.5 s, a problem longer, as the standard has it). `action`:
        (its word, what it does), drawn as a capsule after the words."""
        text = one_stop(text) if tone != "job" else text
        self.text, self.tone = text, tone if tone in self.TONES else ""
        self._action_word, self._action = action if action is not None else ("", None)
        if self.tone != "job":
            self._frac = None
        spin = self.tone == "job" and self._frac is None
        if spin and self._turn.state() != QVariantAnimation.State.Running:
            self._turn.setDuration(tokens.SPINNER_TURN_SLOW_MS if access.reduce_motion() else tokens.SPINNER_TURN_MS)
            self._turn.start()
        elif not spin:
            self._turn.stop()
        ms = ms or (
            tokens.TOAST_UNDO_MS
            if self._action is not None
            else tokens.TOAST_WARN_MS
            if self.tone == "problem"
            else tokens.TOAST_MS
        )
        self._ms = max(ms, len(text) * tokens.TOAST_MS_PER_CHAR)
        lasts = self.lasts()
        takes_clicks = self.tone == "error" or self._action is not None  # an error: a click closes it; else its capsule
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not takes_clicks)
        self.setCursor(Qt.CursorShape.PointingHandCursor if self.tone == "error" else Qt.CursorShape.ArrowCursor)
        self.setToolTip(theme.plain_tip("Close") if self.tone == "error" else "")
        self.place()
        self.raise_()
        # already up (progress, say): just new words, no new entrance
        if not self.isVisible() or self._leaving:
            self._leaving = False
            self._go(1.0, tokens.TOAST_IN_MS, QEasingCurve.Type.OutCubic)
        self.show()
        self.update()
        if lasts:
            self._t.stop()
        else:
            self._t.start(self._ms)
        self.setAccessibleName(text)
        announce(self, text)

    def lasts(self) -> bool:
        """An error that needs you stays until you close it; a job, until it's over."""
        return self.tone in ("error", "job")

    def mousePressEvent(self, e) -> None:
        if self.tone == "error" and self._pill.contains(e.position()):
            self.dismiss()
            e.accept()
            return
        if self._action is not None and self._action_rect.contains(e.position()):
            act, self._action = self._action, None
            if self.tone == "job":
                self.text = "Stopping…"
                self.place()
                self.update()
            else:
                self.dismiss()
            QTimer.singleShot(0, self, act)  # once the click is over (what it does may change this toast)
            e.accept()
            return
        super().mousePressEvent(e)

    def dismiss(self) -> None:
        self._turn.stop()
        if self.isVisible() and not self._leaving:
            self._t.stop()
            self._leaving = True
            self._go(0.0, tokens.TOAST_OUT_MS, QEasingCurve.Type.InCubic)

    def place(self) -> None:
        """Size it to its words and centre it over the bottom of the page."""
        area = self.anchor()
        m = glass.shadow_margin()
        icon_w = self._lead_w() + self._close_w()
        pad_x, pad_y = tokens.SPACE_4, tokens.SPACE_3
        widest = max(tokens.ICON, min(tokens.TOAST_MAX_W, area.width() - 2 * tokens.SPACE_5) - 2 * pad_x - icon_w)
        flags = int(Qt.TextFlag.TextWordWrap)
        box = QFontMetrics(self._font()).boundingRect(QRect(0, 0, widest, 10_000), flags, self.text)
        if self.tone == "job":  # its words don't jump about as the numbers in them change
            box.setWidth(max(box.width(), min(widest, tokens.TOAST_MAX_W // 2)))
        w = icon_w + min(widest, box.width()) + 2 * pad_x
        h = max(tokens.ICON, box.height()) + 2 * pad_y + self._bar_room()
        self._pill = QRectF(m, m, w, h)
        self._action_rect = self._action_at(self._pill)  # where a click takes it (set here, not when it's drawn:
        self.setGeometry(  # a click can come before the first paint, or while it rises)
            round(area.center().x() - w / 2 - m),
            area.bottom() - tokens.TOAST_LIFT - h - m,
            w + 2 * m,
            h + 2 * m,
        )

    @staticmethod
    def _font():
        return theme.font(tokens.TEXT_MD, tokens.WEIGHT_MEDIUM)

    def _lead_w(self) -> int:
        """The room before its words: its tone's icon, a job's spinner, or nothing (a job with a bar)."""
        if self.tone == "job":
            return tokens.SPINNER_SM + tokens.SPACE_2 if self._frac is None else 0
        return tokens.ICON + tokens.SPACE_2

    def _action_w(self) -> int:
        return QFontMetrics(self._font()).horizontalAdvance(self._action_word) + 2 * tokens.SPACE_2_5

    def _close_w(self) -> int:
        """The room after its words: an error's ✕, or a job's Stop."""
        if self.tone == "error":
            return tokens.SPACE_3 + tokens.ICON_SM
        if self._action is not None:
            return tokens.SPACE_3 + self._action_w()
        return 0

    def _bar_room(self) -> int:
        return tokens.SPACE_2 + tokens.BAR_H if self.tone == "job" and self._frac is not None else 0

    def _go(self, to: float, ms: int, curve) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._shown)
        self._anim.setEndValue(to)
        self._anim.setDuration(ms)
        self._anim.setEasingCurve(curve)
        self._anim.start()

    def _step(self, v) -> None:
        self._shown = float(v)
        self.update()

    def _settled(self) -> None:
        if self._leaving:
            self._leaving = False
            self.hide()

    def _time_up(self) -> None:
        if self._pill.contains(QPointF(self.mapFromGlobal(QCursor.pos()))):
            self._t.start(tokens.TOAST_MS)  # you're reading it
        else:
            self.dismiss()

    def paintEvent(self, _e):
        if self._shown <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._shown)
        rise = 0 if access.reduce_motion() else tokens.TOAST_RISE  # Reduce Motion: it fades, never rises
        r = self._pill.translated(0, (1 - self._shown) * rise)
        glass.paint_shadow(p, r, tokens.RADIUS_LG, tokens.TOAST_SHADOW)
        problem = self.tone in ("problem", "error")
        path = QPainterPath()
        path.addRoundedRect(r, tokens.RADIUS_LG, tokens.RADIUS_LG)
        p.fillPath(path, theme.qcolor(tokens.TOAST_PROBLEM_FILL if problem else tokens.TOAST))
        edge = QPainterPath()
        edge.addRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), tokens.RADIUS_LG - 0.5, tokens.RADIUS_LG - 0.5)
        p.setPen(QPen(theme.qcolor(tokens.TOAST_PROBLEM_EDGE if problem else tokens.TOAST_EDGE), 1))
        p.drawPath(edge)
        name, color = self.TONES[self.tone]
        pad_x = tokens.SPACE_4
        words_r = r.adjusted(0, 0, 0, -self._bar_room())  # (a job's bar goes under its words)
        if name:
            icon = theme.icon(name, getattr(tokens, color), tokens.ICON).pixmap(
                QSize(tokens.ICON, tokens.ICON), self.devicePixelRatioF()
            )
            p.drawPixmap(QPointF(r.left() + pad_x, words_r.center().y() - tokens.ICON / 2), icon)
        elif self.tone == "job" and self._frac is None:
            self._paint_spinner(p, QPointF(r.left() + pad_x + tokens.SPINNER_SM / 2, words_r.center().y()))
        text = words_r.adjusted(pad_x + self._lead_w(), 0, -pad_x - self._close_w(), 0)
        p.setFont(self._font())
        p.setPen(theme.qcolor(tokens.TOAST_TEXT))
        p.drawText(text, int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignVCenter), self.text)
        self._paint_action(p, r, words_r)
        if self.tone == "job":
            self._paint_bar(p, words_r, text)
        elif self.tone == "error":
            s = tokens.ICON_SM
            close = theme.icon("x", tokens.TOAST_TEXT, s).pixmap(QSize(s, s), self.devicePixelRatioF())
            p.drawPixmap(QPointF(r.right() - pad_x - s, r.center().y() - s / 2), close)
        p.end()

    def _paint_spinner(self, p: QPainter, centre: QPointF) -> None:
        """G.27's small spinner: a ring with a quarter of it brighter, turning."""
        rad = (tokens.SPINNER_SM - tokens.SPINNER_RING_SM) / 2
        ring = QRectF(centre.x() - rad, centre.y() - rad, 2 * rad, 2 * rad)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(theme.qcolor(tokens.TOAST_TRACK), tokens.SPINNER_RING_SM))
        p.drawEllipse(ring)
        pen = QPen(theme.qcolor(tokens.TOAST_TEXT), tokens.SPINNER_RING_SM)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        angle = float(self._turn.currentValue() or 0.0)
        p.drawArc(ring, int((90 - angle) * 16), -90 * 16)

    def _action_at(self, r: QRectF) -> QRectF:
        """Its capsule's place in a pill at `r` (none without an action)."""
        if self._action is None:
            return QRectF()
        words_r = r.adjusted(0, 0, 0, -self._bar_room())
        sw, sh = self._action_w(), tokens.SMALL_H + tokens.SPACE_1
        return QRectF(r.right() - tokens.SPACE_4 - sw, words_r.center().y() - sh / 2, sw, sh)

    def _paint_action(self, p: QPainter, r: QRectF, words_r: QRectF) -> None:
        """Its capsule after the words (a job's Stop, a delete's Undo), in the toast's own light colors: on the
        dark toast the accent would be too faint to read."""
        cap_r = self._action_at(r)
        if cap_r.isEmpty():
            return
        cap = QPainterPath()
        cap.addRoundedRect(cap_r, cap_r.height() / 2, cap_r.height() / 2)
        p.fillPath(cap, theme.qcolor(tokens.TOAST_BUTTON))
        p.setPen(theme.qcolor(tokens.TOAST_TEXT))
        p.drawText(cap_r, int(Qt.AlignmentFlag.AlignCenter), self._action_word)

    def _paint_bar(self, p: QPainter, words_r: QRectF, text: QRectF) -> None:
        """A job's bar under its words, when how far it is is known."""
        if self._frac is not None:
            right = self._action_rect.right() if self._action is not None else text.right()
            track = QRectF(
                text.left(), words_r.bottom() - tokens.SPACE_3 + tokens.SPACE_2, right - text.left(), tokens.BAR_H
            )
            for part, color in (
                (track, tokens.TOAST_TRACK),
                (QRectF(track.left(), track.top(), track.width() * self._frac, track.height()), tokens.TOAST_TEXT),
            ):
                if part.width() > 0:
                    path = QPainterPath()
                    path.addRoundedRect(part, tokens.BAR_H / 2, tokens.BAR_H / 2)
                    p.fillPath(path, theme.qcolor(color))


# Dropdowns
def combo(items: list[tuple[str, str, str]], current: str) -> QComboBox:
    """The standard dropdown. items: (key, label, tooltip); the key is the item's data."""
    c = QComboBox()
    for key, label, tip in items:
        c.addItem(label, key)
        if tip:
            c.setItemData(c.count() - 1, tip, Qt.ItemDataRole.ToolTipRole)
    c.setCurrentIndex(max(0, c.findData(current)))
    c.setCursor(Qt.CursorShape.PointingHandCursor)
    return c


class Embeddable:
    """A dialog that can also sit inside another window (a Settings pane): no title of its own, no Cancel,
    and finishing (Save, Delete, Sign In) tells its host instead of closing. Dialogs name the parts:
    `title_label` and `cancel_btn`."""

    embedded = False

    def embed(self) -> None:
        self.embedded = True
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setObjectName("Embedded")  # no background of its own: the window's shows through
        for name in ("title_label", "cancel_btn"):
            w = getattr(self, name, None)
            if w is not None:
                w.hide()

    def keyPressEvent(self, e) -> None:
        if self.embedded and e.key() == Qt.Key.Key_Escape:
            e.ignore()  # Esc closes the window it sits in, not the pane
            return
        super().keyPressEvent(e)

    def done(self, r: int) -> None:
        if not self.embedded:
            super().done(r)
            return
        self.setResult(r)
        self.finished.emit(r)
        (self.accepted if r else self.rejected).emit()


class Guarded:
    """A form with its own Save never drops what was typed in it without asking. It gives `form_values()` (what
    it holds now, comparable) and calls `settled()` once it's filled in; a value typed back to what it was counts
    as no change. Cancel, Esc and closing leave at once when nothing changed and otherwise ask Discard Changes /
    Keep Editing; a window it sits in asks `may_leave()` before showing something else."""

    _settled: object = None

    def form_values(self) -> object:
        raise NotImplementedError

    def settled(self) -> None:
        self._settled = self.form_values()

    def unsaved(self) -> bool:
        return self._settled is not None and self.form_values() != self._settled

    def may_leave(self) -> bool:
        from bodega.ui.dialogs.common import ask_discard

        return not self.unsaved() or ask_discard(self)

    def reject(self) -> None:  # Cancel, Esc and the window's close button all come here
        if self.may_leave():
            super().reject()


class ReturnMovesOn(QObject):
    """In a form, Return moves to the next field as Tab does, and on the last one presses `confirm`; ⌘Return
    (Ctrl+Return) presses it from any field. A multi-line box keeps Return for a new line."""

    FIELDS = (QLineEdit, QComboBox, QAbstractSpinBox, QPlainTextEdit)

    def __init__(self, form: QWidget, confirm: QPushButton):
        super().__init__(form)
        self.form, self.confirm = form, confirm
        form.installEventFilter(self)  # (fields added later: their Return comes up to the form)
        for f in form.findChildren(QWidget):
            if isinstance(f, self.FIELDS):  # a multi-line box keeps ⌘Return to itself otherwise
                f.installEventFilter(self)

    def eventFilter(self, obj, e) -> bool:
        if e.type() != QEvent.Type.KeyPress or e.key() not in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return False
        here = obj if isinstance(obj, self.FIELDS) else self.form.focusWidget()
        if not isinstance(here, self.FIELDS) or not self.form.isAncestorOf(here):
            return False
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:  # ⌘Return on a Mac
            self.confirm.click()
            return True
        if isinstance(here, QPlainTextEdit):
            return False
        w = here.nextInFocusChain()
        while w is not here and w is not self.confirm:
            if isinstance(w, self.FIELDS) and self._reachable(w):
                w.setFocus(Qt.FocusReason.TabFocusReason)
                return True
            w = w.nextInFocusChain()
        self.confirm.click()  # the last field
        return True

    def _reachable(self, w: QWidget) -> bool:
        return (
            self.form.isAncestorOf(w)
            and w.isVisibleTo(self.form)
            and w.isEnabled()
            and bool(w.focusPolicy() & Qt.FocusPolicy.TabFocus)
        )


class SearchField(QLineEdit):
    """Every search: asks for SEARCH_W, gives way down to SEARCH_MIN on a narrow window. ↑ and ↓ move through the
    rows of the list it searches while the cursor stays here (`step_wanted`: -1 or 1), so Return can open the one
    marked (the standard's 6.1). Esc is one layer at a time, here for every search: its words go first; then,
    with `leave_to` set, the focus goes there (the list it searches); otherwise Esc goes on to the window (a
    dialog closes)."""

    step_wanted = Signal(int)
    leave_to = None  # () -> None: where an Esc in an empty search takes the focus

    def sizeHint(self) -> QSize:
        return QSize(tokens.SEARCH_W, super().sizeHint().height())

    def _esc_is_mine(self) -> bool:
        return bool(self.text()) or self.leave_to is not None

    def event(self, e):
        if e.type() == QEvent.Type.ShortcutOverride and e.key() == Qt.Key.Key_Escape and self._esc_is_mine():
            e.accept()  # the window's own Esc waits: this layer goes first
            return True
        return super().event(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up) and not e.modifiers() & ~Qt.KeyboardModifier.KeypadModifier:
            self.step_wanted.emit(1 if e.key() == Qt.Key.Key_Down else -1)
            return
        if e.key() == Qt.Key.Key_Escape and not e.modifiers() and self._esc_is_mine():
            if self.text():
                self.clear()
            else:
                self.leave_to()
            return
        super().keyPressEvent(e)


class ListSearch(SearchField):
    """The search over a panel's own list (a kit's gear, a rental's lines), for when it's long: shown once there
    are more than LIST_SEARCH_ABOVE rows (the standard's rule for every list), it hides the rows that don't
    match what's typed, and says so when none do. Put `.box` above the rows; give it the rows with show_for()
    each time they're built."""

    def __init__(self, what: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setPlaceholderText(f"Search {what}")
        self.setAccessibleName(f"Search {what}")
        self.setClearButtonEnabled(True)
        self.addAction(theme.icon("search", theme.FAINT), QLineEdit.ActionPosition.LeadingPosition)
        self.box = QWidget()
        lay = vbox(self.box, (0, 0, 0, tokens.SPACE_2), tokens.SPACE_2)
        lay.addWidget(self)
        self.none = hint("")
        self.none.hide()
        lay.addWidget(self.none)
        self.box.hide()
        self._layout: QLayout | None = None
        self._rows: list[tuple[QWidget, str]] = []
        self.textChanged.connect(lambda _t: self._apply())

    def show_for(self, layout: QLayout, rows: list[tuple[QWidget, str]]) -> None:
        """The rows as built now, each with the words it's found by. Few enough: no search (and none typed)."""
        from bodega.core import search

        self._layout = layout
        self._rows = [(w, search.folded(words)) for w, words in rows]
        long = len(rows) > tokens.LIST_SEARCH_ABOVE
        self.box.setVisible(long)
        if not long and self.text():
            self.blockSignals(True)
            self.clear()
            self.blockSignals(False)
        self._apply()

    def _apply(self) -> None:
        from bodega.core import search

        wanted = search.words(self.text())
        shown = 0
        for w, hay in self._rows:
            on = search.matches(hay, wanted)
            w.setVisible(on)
            shown += on
        self.none.setText(f"Nothing here matches “{self.text().strip()}”." if wanted and not shown else "")
        self.none.setVisible(bool(wanted) and not shown)
        if self._layout is not None:
            rows_done(self._layout)


def set_combo(c: QComboBox, key: str) -> None:
    """Select the item with this key without firing change signals."""
    c.blockSignals(True)
    c.setCurrentIndex(max(0, c.findData(key)))
    c.blockSignals(False)


def disable_item(c: QComboBox, key: str, why: str) -> None:
    """Grey out one item and say why in its tooltip."""
    i = c.findData(key)
    item = c.model().item(i) if i >= 0 and hasattr(c.model(), "item") else None
    if item is not None:
        item.setEnabled(False)
        item.setToolTip(why)


def suggestions(c):
    """A type-ahead list (QCompleter) in the shared list look: rounded, rows inset like the sidebar's."""
    pop = c.popup()
    pop.setObjectName("Suggestions")
    pop.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    pop.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
    pop.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    pop.setItemDelegate(ComboItemDelegate(pop))
    return c


class ComboItemDelegate(QStyledItemDelegate):
    """Draws dropdown rows: rounded highlight from the stylesheet, standard row height,
    and a thin line for separators (Qt's default painter ignores the stylesheet on macOS)."""

    ROW_H = tokens.LIST_ROW_H + tokens.LIST_GAP
    SEP_H = tokens.SPACE_2 + 1

    @staticmethod
    def _is_separator(index) -> bool:
        return index.data(Qt.ItemDataRole.AccessibleDescriptionRole) == "separator"

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(self.SEP_H if self._is_separator(index) else max(size.height(), self.ROW_H))
        return size

    def paint(self, painter, option, index):
        if self._is_separator(index):
            y = option.rect.center().y()
            painter.save()
            painter.setPen(theme.qcolor(tokens.BORDER_STRONG))
            painter.drawLine(
                option.rect.left() + tokens.SPACE_2,
                y,
                option.rect.right() - tokens.SPACE_2,
                y,
            )
            painter.restore()
            return
        super().paint(painter, option, index)


class FitScroll(QScrollArea):
    """Scroll area whose content always matches the visible width (no clipped edges).

    The scroll bar's space is always reserved (it's invisible while there's nothing to scroll), so
    content never shifts or squeezes when a group opens. Put SCROLL_GUTTER less margin on the
    right of the content so both sides look the same."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        bar = self.verticalScrollBar()
        bar.setEnabled(False)
        bar.rangeChanged.connect(lambda lo, hi: bar.setEnabled(hi > lo))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.widget():
            self.widget().setFixedWidth(self.viewport().width())


class PanelHeader(QFrame):
    """The top of each panel, the same height everywhere so the three panels line up.

    It says what the panel holds ("Item", "Rental Agreement"), or holds a control instead of a title (the
    Gear / Packages / Rentals switch). `.lead` takes widgets on the left, `.actions` on the right."""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("PanelHeader")
        self.setFixedHeight(tokens.HEADER_H)
        lay = hbox(self, (tokens.SPACE_4, 0, tokens.SPACE_4, 0), tokens.SPACE_2)
        self.title = QLabel(title)
        self.title.setObjectName("PanelTitle")
        self.title.setVisible(bool(title))
        lay.addWidget(self.title)
        self.lead = hbox(spacing=tokens.SPACE_2)
        lay.addLayout(self.lead, 1)
        self.actions = hbox(spacing=tokens.SPACE_2)
        lay.addLayout(self.actions)

    def set_title(self, title: str) -> None:
        self.title.setText(title)
        self.title.setVisible(bool(title))

    def add_close(self, tip: str = "Close") -> QToolButton:
        """The round ✕, at the far right (after the ⋯ and any other buttons)."""
        b = circle_button("x", tip)
        self.layout().addWidget(b)
        return b


def by_keyboard(w: QWidget, act, e) -> bool:
    """For a row that's clickable (a section head, a line's head, a piece that goes with this one): Return or
    Space does what a click does, once the key is over (a refresh may rebuild the row). True if it was one."""
    if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space) and not e.modifiers():
        QTimer.singleShot(0, w, act)
        return True
    return False


class ToggleRow(QAbstractButton):
    """An on/off setting: the label on the left, a switch on the right, the whole row clickable.
    Works like a QCheckBox (setChecked, isChecked, toggled, text)."""

    def __init__(self, text: str, checked: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(tokens.TOGGLE_ROW_H)
        self._hover = False

    def sizeHint(self) -> QSize:
        w = self.fontMetrics().horizontalAdvance(self.text()) + tokens.SPACE_3 + tokens.TOGGLE_W
        return QSize(w, tokens.TOGGLE_ROW_H)

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        on, enabled = self.isChecked(), self.isEnabled()
        r = self.rect()
        # label
        p.setPen(theme.qcolor(tokens.TEXT if enabled else tokens.TEXT_OFF))
        text_rect = r.adjusted(0, 0, -(tokens.TOGGLE_W + tokens.SPACE_3), 0)
        label = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, text_rect.width())
        p.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            label,
        )
        # switch
        tw, th = tokens.TOGGLE_W, tokens.TOGGLE_H
        track = QRectF(r.right() - tw + 1, r.center().y() - th / 2 + 1, tw - 1, th - 1)
        fill = tokens.GOOD_FILL if on else tokens.FILL_3  # an on switch is green, as Apple's are
        if not enabled:
            fill = tokens.GOOD_OFF if on else tokens.TRACK_OFF
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.qcolor(fill))
        p.drawRoundedRect(track, th / 2, th / 2)
        knob = th - 2 * tokens.TOGGLE_INSET
        x = track.right() - tokens.TOGGLE_INSET - knob if on else track.left() + tokens.TOGGLE_INSET
        p.setBrush(theme.qcolor(tokens.KNOB if enabled else tokens.KNOB_OFF))  # white, on or off
        p.drawEllipse(QRectF(x, track.top() + tokens.TOGGLE_INSET, knob, knob))
        if self.hasFocus():  # the keyboard is on it: its ring, around the switch
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(theme.qcolor(tokens.ACCENT), tokens.FOCUS_RING))
            ring = track.adjusted(-tokens.FOCUS_GAP, -tokens.FOCUS_GAP, tokens.FOCUS_GAP, tokens.FOCUS_GAP)
            p.drawRoundedRect(ring, ring.height() / 2, ring.height() / 2)
        p.end()


class TextBox(QPlainTextEdit):
    """A multi-line text field (addresses, details, payment text) that looks like the one-line fields.
    `edited` fires on typing only, never when the window fills it in with set_text()."""

    edited = Signal()

    def __init__(
        self,
        placeholder: str = "",
        height: int = tokens.TEXT_BOX_H,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("Field")
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(height)
        self.setTabChangesFocus(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._quiet = False
        self.textChanged.connect(self._changed)

    def _changed(self) -> None:
        if not self._quiet:
            self.edited.emit()

    def text(self) -> str:
        return self.toPlainText()

    def set_text(self, text: str) -> None:
        if text == self.toPlainText():
            return
        self._quiet = True
        self.setPlainText(text)
        self._quiet = False


class TitleEdit(QPlainTextEdit):
    """A big, editable title that wraps onto a second line instead of being cut off. One line of text (Return
    finishes, pasted line breaks become spaces); it grows to fit. Works like a QLineEdit: text(), setText(),
    textEdited (typing only)."""

    textEdited = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("BigName")
        self.setTabChangesFocus(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._quiet = False
        self.textChanged.connect(self._changed)

    def _changed(self) -> None:
        self._fit()
        if self._quiet:
            return
        t = self.toPlainText()
        if "\n" in t:  # a pasted line break
            pos = self.textCursor().position()
            self.setText(" ".join(t.split()))
            self.setCursorPosition(min(pos, len(self.toPlainText())))
            t = self.toPlainText()
        self.textEdited.emit(t)

    def _fit(self) -> None:
        """As tall as its lines are laid out (a line is a fraction taller than the font's whole-pixel line
        spacing): a box a pixel short could scroll inside itself, hiding the first line of a two-line name."""
        doc = self.document()
        h = 0.0
        block = doc.begin()
        while block.isValid():
            h += self.blockBoundingRect(block).height()  # the last one takes the bottom margin
            block = block.next()
        m = self.contentsMargins()
        self.setFixedHeight(math.ceil(h + doc.documentMargin()) + 1 + m.top() + m.bottom())  # the top margin

    def text(self) -> str:
        return self.toPlainText()

    def setText(self, text: str) -> None:
        self._quiet = True
        self.setPlainText(text)
        self._quiet = False
        self._fit()

    def setCursorPosition(self, n: int) -> None:
        c = self.textCursor()
        c.setPosition(n)
        self.setTextCursor(c)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clearFocus()
            return
        super().keyPressEvent(e)

    def wheelEvent(self, e):
        e.ignore()  # it shows all of itself, so the wheel scrolls the panel it's in

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() in (e.Type.FontChange, e.Type.StyleChange):
            self._fit()


# Fields shared by the panels
def date_field():
    """Every date: typed or picked from its month (components/datefield.py, the standard's G.22)."""
    from bodega.ui.components.datefield import DateField

    return DateField()


def to_qdate(iso: str):
    from bodega.core import dates

    d = dates.parse(iso) or dates.today()
    return QDate(d.year, d.month, d.day)


def from_qdate(q) -> str:
    return f"{q.year():04d}-{q.month():02d}-{q.day():02d}"


def button_row() -> QHBoxLayout:
    """The row of buttons at the bottom of a dialog: right-aligned (add the main one last), SPACE_4 below
    the content in every dialog (dialogs lay out with SPACE_3 between rows)."""
    row = hbox(spacing=tokens.SPACE_2)
    row.setContentsMargins(0, tokens.SPACE_4 - tokens.SPACE_3, 0, 0)
    row.addStretch(1)
    return row


class IconLabel(QLabel):
    """A small icon that isn't a button. `tone` names a theme color ("MUTED", "ACCENT", "BAD"…); it redraws
    itself when the look changes between light and dark."""

    def __init__(self, name: str = "", tone: str = "MUTED", size: int = tokens.ICON_SM, parent=None):
        super().__init__(parent)
        self._name, self._tone, self._size = name, tone, size
        self.setFixedSize(size, size)
        self._draw()

    def set_icon(self, name: str) -> None:
        if name != self._name:
            self._name = name
            self._draw()

    def set_tone(self, tone: str) -> None:
        if tone != self._tone:
            self._tone = tone
            self._draw()

    def _draw(self) -> None:
        if self._name:
            self.setPixmap(theme.pixmap(self._name, self._size, getattr(theme, self._tone)))
        else:
            self.clear()

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == e.Type.StyleChange:  # the app's stylesheet changed: light or dark
            self._draw()


def circle_button(name: str, tip: str, color: str = "") -> QToolButton:
    """The standard icon button: a round, raised button the height of every control (toolbars, panel
    headers, ‹ › arrows). Always has a tooltip."""
    b = QToolButton()
    b.setObjectName("Circle")
    b.setIcon(theme.icon(name, color or theme.MUTED))
    b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def icon_button(name: str, tip: str, color: str = "", size: int = tokens.ICON_SM):
    """A small icon button inside a row or a card (a line's ⋯): round, no frame until you point at it.
    Always has a tooltip. Without a `color` it's the muted grey of the look in use
    (read now, not when this file loaded, so light mode gets light mode's grey)."""

    b = QToolButton()
    b.setObjectName("IconBtn")
    b.setIcon(theme.icon(name, color or theme.MUTED, size))
    b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


class Picker(QComboBox):
    """A dropdown of your own things (profiles, renters, groups). Past LIST_SEARCH_ABOVE choices, opening it
    opens a list you can search instead (dialogs.common.pick_from), once the click is over."""

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.title = title

    def _rows(self) -> list[int]:
        return [
            i for i in range(self.count()) if self.itemData(i, Qt.ItemDataRole.AccessibleDescriptionRole) != "separator"
        ]

    def showPopup(self) -> None:
        if len(self._rows()) <= tokens.LIST_SEARCH_ABOVE:
            super().showPopup()
            return
        QTimer.singleShot(0, self, self._search)

    def _search(self) -> None:
        from bodega.ui.dialogs.common import pick_from

        rows = [(str(i), self.itemText(i)) for i in self._rows()]
        picked = pick_from(self.window(), self.title, rows, "Choose", current=str(self.currentIndex()))
        if picked is not None:
            self.setCurrentIndex(int(picked))
            self.activated.emit(int(picked))


def picker(placeholder: str = "", title: str = "Choose") -> Picker:
    """A dropdown of your own things (profiles, renters) that never widens the panel for a long name."""
    c = Picker(title)
    c.setCursor(Qt.CursorShape.PointingHandCursor)
    c.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    c.setMinimumContentsLength(1)
    c.setPlaceholderText(placeholder)
    return c


class QtyField(QLineEdit):
    """A whole number of pieces, typed. Works like a spin box (value, setValue, valueChanged), and the
    arrow keys count up and down."""

    valueChanged = Signal(int)

    def __init__(self, value: int = 1, top: int = MAX_QTY, parent: QWidget | None = None):
        super().__init__(parent)
        from PySide6.QtGui import QIntValidator

        self._top = top
        self._value = max(1, value)
        self.setValidator(QIntValidator(1, top, self))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(tokens.QTY_FIELD_W)
        self.setText(str(self._value))
        self.textEdited.connect(self._typed)
        self.editingFinished.connect(lambda: self.setText(str(self._value)))

    def value(self) -> int:
        return self._value

    def setValue(self, v: int) -> None:
        v = min(self._top, max(1, int(v)))
        self.setText(str(v))
        if v != self._value:
            self._value = v
            self.valueChanged.emit(v)

    def _typed(self, text: str) -> None:
        if text.isdigit() and int(text) >= 1 and int(text) != self._value:
            self._value = min(self._top, int(text))
            self.valueChanged.emit(self._value)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Up:
            self.setValue(self._value + 1)
        elif e.key() == Qt.Key.Key_Down:
            self.setValue(self._value - 1)
        else:
            super().keyPressEvent(e)


def qty_field(value: int = 1, top: int = MAX_QTY) -> QtyField:
    return QtyField(value, top)


def set_tone(lbl: QLabel, tone: str, text: str) -> None:
    if lbl.property("tone") != tone:
        lbl.setProperty("tone", tone)
        repolish(lbl)
    lbl.setText(text)
    lbl.setVisible(bool(text))


PERCENT_TYPED = r"\s*\d{0,3}(\.\d{0,3})?\s*%?\s*"  # "8.875", "15 %"
WHOLE_TYPED = r"\s*\d{0,3}\s*"  # a count of days
COUNT_TYPED = r"\s*\d{0,5}\s*"  # a bigger count (questions to your AI a day)


def only(field: QLineEdit, pattern: str) -> QLineEdit:
    """Typing is kept to what the field can read: a letter is never quietly read as 0."""
    from PySide6.QtCore import QRegularExpression
    from PySide6.QtGui import QRegularExpressionValidator

    field.setValidator(QRegularExpressionValidator(QRegularExpression(pattern), field))
    return field


FIELD_KINDS = {"name": "ROW_CTL", "short": "ROW_CTL_SHORT"}  # the standard's widths, by what a field holds


def sized(w: QWidget, kind: str) -> QWidget:
    """A control sized by what it holds (the standard's 4.6, G.3): "name" (a name, an email, a phone, a link) and
    "short" (a rate, a number, a prefix) are at most their kind's width, so fields of one kind line up; "popup"
    hugs its value. Set per kind, never per control."""
    if kind == "popup":
        if isinstance(w, QComboBox):
            w.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        w.setSizePolicy(QSizePolicy.Policy.Fixed, w.sizePolicy().verticalPolicy())
    else:
        w.setMaximumWidth(getattr(tokens, FIELD_KINDS[kind]))
    return w


def percent_field(text: str = "", placeholder: str = "") -> QLineEdit:
    """A percent (discount, sales tax, a day's rate): digits and one point, the % sign optional."""
    f = only(QLineEdit(text), PERCENT_TYPED)
    f.setPlaceholderText(placeholder)
    return f


class MoneyField(QLineEdit):
    """A money amount: reads "$5,998.00" until you click in, then it's the plain number to type over.
    `value()` is what you typed ("5998"); textEdited still fires with the typed text. Only an amount can be
    typed (digits, commas, a point and cents, the currency sign)."""

    def __init__(self, currency: str = "$", parent: QWidget | None = None):
        super().__init__(parent)
        self.currency = currency
        self._raw = ""
        only(self, rf"\s*{re.escape(currency)}?\s*[\d,]{{0,16}}(\.\d{{0,2}})?\s*")

    def value(self) -> str:
        return self.text() if self.hasFocus() else self._raw

    def set_value(self, raw: str) -> None:
        self._raw = (raw or "").strip()
        self._show()

    def _show(self) -> None:
        from bodega.core import money

        if self.hasFocus() or not self._raw:
            self.setText(self._raw)
            return
        n = money.parse(self._raw)
        self.setText(money.fmt(n, self.currency) if n or self._raw.strip("0.") == "" else self._raw)

    def focusInEvent(self, e):
        self.setText(self._raw)
        super().focusInEvent(e)
        QTimer.singleShot(0, self, self.selectAll)

    def focusOutEvent(self, e):
        self._raw = self.text().strip().replace(self.currency, "").replace(",", "")
        super().focusOutEvent(e)
        self._show()


def primary_button(text: str = "") -> QPushButton:
    """The one button that does what a window is for (Save, Import, Send): the accent fill."""
    b = QPushButton(text)
    b.setObjectName("Primary")
    return b


def add_chip(text: str, icon: str = "plus") -> QPushButton:
    """A tinted capsule with a small icon (+ Link, + Add Gear): the app's "add something" button."""
    b = QPushButton(text)
    b.setObjectName("AddChip")
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setIcon(theme.icon(icon, theme.ACCENT, tokens.ICON_SM))
    return b


class FlowLayout(QLayout):
    """Lays widgets out left to right and wraps to the next line when the row is full (chips)."""

    def __init__(self, parent: QWidget | None = None, spacing: int = tokens.SPACE_2):
        super().__init__(parent)
        self._items: list = []
        self._space = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._lay(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect) -> None:
        super().setGeometry(rect)
        self._lay(rect, apply=True)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for it in self._items:
            size = size.expandedTo(it.minimumSize())
        return size

    def _lay(self, rect, apply: bool) -> int:
        x, y, line = rect.x(), rect.y(), 0
        for it in self._items:
            if it.widget() is not None and not it.widget().isVisibleTo(it.widget().parentWidget()):
                continue
            hint = it.sizeHint()
            if x + hint.width() > rect.right() + 1 and line > 0:
                x, y, line = rect.x(), y + line + self._space, 0
            if apply:
                it.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._space
            line = max(line, hint.height())
        return y + line - rect.y()
