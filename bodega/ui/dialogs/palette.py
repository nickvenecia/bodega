"""Search Everything (⌘K / Ctrl+K, or the sidebar's Search): places, gear, kits and rentals, and every command in the
menus, from one field (the standard's §4.8 and G.23). Results come in groups, places first, then records, then
commands; ↓ ↑ move and wrap, Home and End jump, Return runs, Esc closes; the pointer moves the highlight.

What it finds a record by is the list's own (core/search: gear_hay, kit_hay, rental_hay), so the palette and the
lists always agree. Commands are read from the menu bar itself, so every command (the menu bar is hidden on Windows
and Linux) has a way in, and the palette is never out of date. It runs the choice once it has closed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from PySide6.QtCore import QEvent, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QStyle,
    QStyledItemDelegate,
    QWidget,
)

from bodega.core import pricing, search
from bodega.ui.components import sheet
from bodega.ui.components.widgets import IconLabel, hbox, vbox
from bodega.ui.style import theme, tokens

GROUP_SHOWN = 8  # records of one kind shown at a time (type more to narrow them)
ROLE = Qt.ItemDataRole.UserRole  # a row's Hit (None on a group heading)


@dataclass
class Hit:
    group: str  # "Go To", "Gear", "Kits", "Rentals", "Commands"
    title: str
    detail: str
    icon: str
    hay: str  # folded words it's found by
    run: Callable[[], None]


def _menu_commands(window) -> list[Hit]:
    """Every command in the menu bar that can run now, with its menu and its key as the detail."""
    out: list[Hit] = []

    def walk(menu: QMenu, where: str) -> None:
        for a in menu.actions():
            if a.isSeparator() or not a.isVisible():
                continue
            if a.menu() is not None:
                walk(a.menu(), a.text().replace("&", ""))
                continue
            if not a.isEnabled() or not a.text().strip():
                continue
            text = a.text().replace("&&", "\0").replace("&", "").replace("\0", "&")
            keys = a.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
            detail = f"{where} · {keys}" if keys else where
            out.append(Hit("Commands", text, detail, "terminal", search.folded(f"{text} {where}"), _trigger(a)))

    bar = window.menuBar()
    for top in bar.actions():
        if top.menu() is not None:
            walk(top.menu(), top.text().replace("&", ""))
    return out


def _trigger(a: QAction) -> Callable[[], None]:
    return lambda: a.trigger()


def hits(window, typed: str) -> list[Hit]:
    """What the palette shows for what's typed: places, then records, then commands (all of them, empty)."""
    from bodega.ui.window.common import PLACES

    wanted = search.words(typed)
    lib = window.lib
    found: list[Hit] = []
    for p in PLACES:
        found.append(
            Hit("Go To", p.title, "", p.icon or "chevron-right", search.folded(p.title), lambda k=p.key: window.go(k))
        )
    for g in lib.groups():
        found.append(Hit("Go To", g, "Group", "folder", search.folded(f"{g} group"), lambda k=f"grp:{g}": window.go(k)))
    if wanted:  # records only once something's typed
        names = {it.id: it.name for it in lib.items.values()}
        gear = [
            Hit("Gear", it.name or "Untitled Piece", " · ".join(x for x in (it.brand, it.group) if x), "box",
                search.gear_hay(it, names.get(it.parent, "")), lambda i=it.id: window.open("gear", i))
            for it in lib.ordered_items()
            if not it.is_retired()
        ]  # fmt: skip
        kits = [
            Hit("Kits", p.name or "Untitled Kit", "Kit", "case", search.kit_hay(p),
                lambda i=p.id: window.open("packages", i))
            for p in lib.packages.values()
        ]  # fmt: skip
        rentals = [
            Hit("Rentals", r.number or "Rental", " · ".join(x for x in (r.client.company or r.client.name, r.project) if x),
                "receipt", search.rental_hay(r), lambda i=r.id: window.open("rentals", i))
            for r in sorted(lib.rentals.values(), key=lambda r: pricing.span_of(r)[0] or date.min, reverse=True)
        ]  # fmt: skip
        for kind in (gear, kits, rentals):
            found += [h for h in kind if search.matches(h.hay, wanted)][:GROUP_SHOWN]
    found += _menu_commands(window)
    return [h for h in found if search.matches(h.hay, wanted)]


class _Rows(QStyledItemDelegate):
    """A palette row: a CHOICE_ROW_H row, inset, with its icon, words and a faint detail on the right; the
    highlighted row the accent's wash. Group headings in small faint words."""

    def sizeHint(self, option, index) -> QSize:
        head = index.data(ROLE) is None
        return QSize(0, tokens.PALETTE_HEAD_H if head else tokens.LIST_ROW_H)

    def paint(self, painter: QPainter, option, index) -> None:
        hit: Hit | None = index.data(ROLE)
        r = option.rect
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if hit is None:
            painter.setFont(theme.font(tokens.TEXT_SUBHEAD, tokens.WEIGHT_SEMIBOLD))
            painter.setPen(theme.qcolor(tokens.MUTED))
            text = r.adjusted(tokens.PALETTE_TEXT_X, 0, 0, -tokens.SPACE_1)
            painter.drawText(text, int(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft), index.data())
            painter.restore()
            return
        on = bool(option.state & QStyle.StateFlag.State_Selected)
        if on:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.qcolor(tokens.ACCENT_TINT))
            painter.drawRoundedRect(QRectF(r), tokens.LIST_ROW_R, tokens.LIST_ROW_R)
        size = tokens.PALETTE_ICON
        icon = theme.pixmap(hit.icon, size, tokens.ACCENT if on else tokens.MUTED)
        painter.drawPixmap(r.left() + tokens.SPACE_3, r.center().y() - size // 2, icon)
        detail_w = 0
        painter.setFont(theme.font(tokens.TEXT_CALLOUT))
        if hit.detail:
            fm = painter.fontMetrics()
            detail = fm.elidedText(hit.detail, Qt.TextElideMode.ElideLeft, r.width() // 3)
            detail_w = fm.horizontalAdvance(detail) + tokens.SPACE_3
            painter.setPen(theme.qcolor(tokens.MUTED))
            box = r.adjusted(0, 0, -tokens.SPACE_3, 0)
            painter.drawText(box, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight), detail)
        painter.setFont(theme.font(tokens.TEXT_BODY))
        painter.setPen(theme.qcolor(tokens.ACCENT_TEXT if on else tokens.TEXT))
        words = QRect(
            r.left() + tokens.PALETTE_TEXT_X, r.top(), r.width() - tokens.PALETTE_TEXT_X - detail_w, r.height()
        )
        title = painter.fontMetrics().elidedText(hit.title, Qt.TextElideMode.ElideRight, words.width())
        painter.drawText(words, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), title)
        painter.restore()


class CommandPalette(QDialog):
    """The palette over a dimmed window: a glass panel PALETTE_TOP from the top, up to PALETTE_W wide."""

    SHEET = False  # it draws its own scrim (a Spotlight panel, near the top)

    def __init__(self, window: QWidget):
        super().__init__(window, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("Search Everything")
        self.window_ = window
        self.chosen: Hit | None = None
        self.panel = QFrame(self)
        self.panel.setObjectName("Palette")
        lay = vbox(self.panel, 0, 0)
        head = self.head = QWidget()
        head.setObjectName("PaletteHead")
        hl = hbox(head, (tokens.PALETTE_PAD_X, tokens.SPACE_3, tokens.PALETTE_PAD_X, tokens.SPACE_3), tokens.SPACE_3)
        hl.addWidget(IconLabel("search", "MUTED", tokens.ICON_LG))
        self.find = QLineEdit()
        self.find.setObjectName("PaletteFind")
        self.find.setPlaceholderText("Search")
        self.find.setAccessibleName("Search places, gear, kits, rentals and commands")
        hl.addWidget(self.find, 1)
        lay.addWidget(head)
        self.list = QListWidget()
        self.list.setObjectName("PaletteList")
        self.list.setItemDelegate(_Rows(self.list))
        self.list.setMouseTracking(True)
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # the keys stay in the field
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.itemEntered.connect(lambda it: it.data(ROLE) is not None and self.list.setCurrentItem(it))
        self.list.itemClicked.connect(lambda it: it.data(ROLE) is not None and self._run(it))
        lay.addWidget(self.list, 1)
        self.none = QLabel()
        self.none.setObjectName("PaletteNone")
        self.none.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.none.hide()
        lay.addWidget(self.none)
        self.find.textChanged.connect(self._fill)
        self.find.installEventFilter(self)
        self._fill("")

    # What it shows
    def _fill(self, typed: str) -> None:
        self.list.clear()
        group = ""
        first = None
        for h in hits(self.window_, typed):
            if h.group != group:
                group = h.group
                head = QListWidgetItem(group)
                head.setFlags(Qt.ItemFlag.NoItemFlags)
                head.setData(ROLE, None)
                self.list.addItem(head)
            it = QListWidgetItem(h.title)
            it.setData(ROLE, h)
            it.setToolTip(theme.plain_tip(h.detail) if h.detail else "")
            self.list.addItem(it)
            first = first or it
        if first is not None:
            self.list.setCurrentItem(first)
        self.none.setText(f"Nothing matches “{typed.strip()}”.")
        self.none.setVisible(first is None and bool(typed.strip()))
        self.list.setVisible(first is not None)
        self._fit()

    def _rows(self) -> list[QListWidgetItem]:
        return [self.list.item(i) for i in range(self.list.count()) if self.list.item(i).data(ROLE) is not None]

    def _step(self, n: int) -> None:
        rows = self._rows()
        if not rows:
            return
        cur = self.list.currentItem()
        i = rows.index(cur) if cur in rows else -1
        self.list.setCurrentItem(rows[(i + n) % len(rows)])  # wraps
        self.list.scrollToItem(self.list.currentItem())

    def _run(self, item: QListWidgetItem | None = None) -> None:
        item = item or self.list.currentItem()
        hit = item.data(ROLE) if item is not None else None
        if hit is None:
            return
        self.chosen = hit
        self.accept()
        QTimer.singleShot(0, self.window_, hit.run)  # once the palette is gone

    def eventFilter(self, obj, e):
        if obj is self.find and e.type() == QEvent.Type.KeyPress:
            k = e.key()
            if k in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                self._step(1 if k == Qt.Key.Key_Down else -1)
                return True
            if k in (Qt.Key.Key_Home, Qt.Key.Key_End) and not e.modifiers():
                rows = self._rows()
                if rows:
                    self.list.setCurrentItem(rows[0] if k == Qt.Key.Key_Home else rows[-1])
                    self.list.scrollToItem(self.list.currentItem())
                return True
            if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._run()
                return True
        return super().eventFilter(obj, e)

    # Where it sits
    def _fit(self) -> None:
        w = self.window_
        self.setGeometry(QRect(w.mapToGlobal(w.rect().topLeft()), w.size()))
        width = min(tokens.PALETTE_W, w.width() - 2 * tokens.SPACE_5)
        rows = sum(self.list.sizeHintForRow(i) for i in range(self.list.count())) + 2 * tokens.SPACE_2_5
        head = self.head.sizeHint().height()
        most = min(tokens.PALETTE_MAX_H, int(w.height() * tokens.PALETTE_MAX_SHARE))
        body = (self.none.sizeHint().height() + 2 * tokens.SPACE_5) if self.none.isVisibleTo(self) else rows
        self.panel.setGeometry((w.width() - width) // 2, tokens.PALETTE_TOP, width, min(most, head + body))

    _still = None  # the window as it was, blurred

    def showEvent(self, e):
        super().showEvent(e)
        self._still = sheet.still(self.window_, tokens.PALETTE_BLUR)
        self._fit()
        self.find.setFocus()

    def paintEvent(self, _e):
        p = QPainter(self)
        if self._still is not None:
            p.drawPixmap(self.rect(), self._still)
        p.fillRect(self.rect(), theme.qcolor(tokens.SCRIM))  # the window, blurred and dimmed under it
        p.end()

    def mousePressEvent(self, e):
        if not self.panel.geometry().contains(e.position().toPoint()):
            self.reject()  # a click outside closes it
            return
        super().mousePressEvent(e)


def open_palette(window) -> Hit | None:
    """Show it over the window; what was chosen runs once it has closed."""
    d = CommandPalette(window)
    d.exec()
    return d.chosen
