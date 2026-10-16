"""The app's two panel kinds, so every one of each looks and behaves the same:

LeftPanel   every list of places on the left (the main sidebar, Settings' sections): floating glass, rows
            (NavRow) inset NAV_INSET from its edges so their corners curve with the glass, an optional top
            (the wordmark), a list that scrolls, an optional foot (the profile card)
SidePanel   every panel on the right (gear, kit, rental details; the assistant): the same header everywhere
            (title, your own round buttons, ⋯ when it has a menu, then the round ✕ at the far right), a body
            that scrolls or not, and a footer for its one main action

Subclass them; change what's inside, never the frame.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QMenu, QPushButton, QToolButton, QWidget

from bodega.ui.components.glass import glass
from bodega.ui.components.widgets import (
    FitScroll,
    IconLabel,
    PanelHeader,
    circle_button,
    hbox,
    repolish,
    vbox,
)
from bodega.ui.style import theme, tokens


class NavRow(QFrame):
    """One place in a LeftPanel: an icon, a name, a count; an arrow when rows fold under it."""

    clicked = Signal(str)
    fold_wanted = Signal(str)  # its arrow (rows with rows under them)
    menu_wanted = Signal(str, QPoint)
    dropped = Signal(str)  # gear dragged from the table onto a department

    def __init__(self, key: str, label: str, icon: str = "", parent: QWidget | None = None, foldable: bool = True):
        """`foldable=False`: a plain list row (Settings) with no room kept for a fold arrow."""
        super().__init__(parent)
        self.key = key
        self.icon_name = icon
        self.setObjectName("Nav")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)  # Tab reaches every place (a click doesn't move the focus)
        self.setFixedHeight(tokens.NAV_H)
        lay = hbox(self, (tokens.SPACE_1 if foldable else tokens.SPACE_2, 0, tokens.SPACE_2, 0), tokens.SPACE_1)
        self.arrow = QToolButton(self)  # shown on rows with rows under them; keeps its room on the others
        self.arrow.setObjectName("NavArrow")
        self.arrow.setFixedSize(tokens.TARGET_MIN, tokens.TARGET_MIN)  # inside a row that's a target too
        self.arrow.setCursor(Qt.CursorShape.PointingHandCursor)
        self.arrow.clicked.connect(lambda: self.fold_wanted.emit(self.key))
        self.arrow.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # the row folds from the keyboard (← →); no extra stop
        self.arrow.setAccessibleName(f"Hide {label}")
        keep = self.arrow.sizePolicy()
        keep.setRetainSizeWhenHidden(True)
        self.arrow.setSizePolicy(keep)
        self.arrow.hide()
        self.folded = False
        if foldable:
            lay.addWidget(self.arrow)
        else:
            lay.setSpacing(tokens.SPACE_2)
        self.icon = IconLabel(icon, "MUTED", tokens.ICON)
        self.recolor()
        self.icon.setFixedWidth(tokens.ICON)
        self.label = QLabel(label)
        self.label.setObjectName("NavLabel")
        self.setAccessibleName(label)  # a screen reader says the place, not "Border"
        self.count = QLabel()
        self.count.setObjectName("NavCount")
        lay.addWidget(self.icon)
        lay.addWidget(self.label, 1)
        lay.addWidget(self.count)

    def recolor(self) -> None:
        self.arrow.setIcon(theme.icon("chevron-right" if self.folded else "chevron", theme.FAINT, tokens.ICON_SM))

    def set_folded(self, on: bool) -> None:
        self.folded = on
        self._folds = True
        self.recolor()
        self._describe()
        self.arrow.setAccessibleName(f"{'Show' if on else 'Hide'} {self.label.text()}")

    def _describe(self) -> None:
        """What a screen reader says after the place's name: its count, then whether it's folded."""
        parts = [self.count.text()] if self.count.text() else []
        if getattr(self, "_folds", False):
            parts.append("Collapsed" if self.folded else "Expanded")
        self.setAccessibleDescription(", ".join(parts))

    def set_label(self, text: str) -> None:
        self.label.setText(text)
        self.setAccessibleName(text)
        self.arrow.setAccessibleName(f"{'Show' if self.folded else 'Hide'} {text}")

    def as_child(self) -> None:
        """A row under another: its name starts where the row above's icon is."""
        self.icon.hide()
        self.label.setObjectName("NavSub")

    def set_count(self, n: int | str, tone: str = "") -> None:
        self.count.setText(str(n) if n not in (0, "") else "")
        self._describe()
        if self.count.property("tone") != tone:
            self.count.setProperty("tone", tone)
            repolish(self.count)

    def set_current(self, on: bool) -> None:
        self.setProperty("current", on)
        self.set_selected(on)

    def set_selected(self, on: bool) -> None:
        if bool(self.property("selected")) != on:
            self.setProperty("selected", on)
            repolish(self)
            repolish(self.label)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(e)

    def keyPressEvent(self, e):
        """From the keyboard: Return or Space opens the place, ↑ ↓ move between places, → ← open and fold."""
        k = e.key()
        if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            QTimer.singleShot(0, self, lambda: self.clicked.emit(self.key))  # once the key is over (rule 16)
        elif k in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            self.focusNextPrevChild(k == Qt.Key.Key_Down)
        elif k in (Qt.Key.Key_Right, Qt.Key.Key_Left) and self.arrow.isVisible():
            if self.folded == (k == Qt.Key.Key_Right):
                self.fold_wanted.emit(self.key)
        else:
            super().keyPressEvent(e)

    def contextMenuEvent(self, e):
        # the menu opens once the right-click is over: Rename Group… or Remove Group there takes this very row
        # away, and a row still busy with its right-click when that happens would crash
        pos = e.globalPos()
        QTimer.singleShot(0, self, lambda: self.menu_wanted.emit(self.key, pos))

    def dragEnterEvent(self, e):
        from bodega.ui.window.tables import GearTable

        if isinstance(e.source(), GearTable):
            e.acceptProposedAction()
            self.set_selected(True)
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self.set_selected(self.property("current") is True)

    def dropEvent(self, e):
        e.setDropAction(Qt.DropAction.IgnoreAction)
        e.accept()
        self.set_selected(self.property("current") is True)
        self.dropped.emit(self.key)


class LeftPanel(QFrame):
    """A list of places on the left. `top_height`: room for a top (the wordmark); 0 for none."""

    def __init__(self, width: int, top_height: int = 0, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        glass(self)
        self.setFixedWidth(width)
        self.rows: dict[str, NavRow] = {}
        outer = vbox(self, 0, 0)
        self.top = QWidget()
        self.top_lay = hbox(self.top, (tokens.SPACE_4, 0, tokens.SPACE_4, 0), 0)
        self.top.setFixedHeight(top_height)
        self.top.setVisible(top_height > 0)
        outer.addWidget(self.top)
        self.scroll = FitScroll()  # its scroll bar's room is the right-hand inset
        body = QWidget()
        inset = tokens.NAV_INSET
        self.lay = vbox(body, (inset, 0 if top_height else inset, inset - tokens.SCROLL_GUTTER, inset), tokens.NAV_GAP)
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll, 1)
        self.foot = QFrame()
        self.foot.setObjectName("SidebarFoot")
        self.foot_lay = vbox(self.foot, inset, tokens.SPACE_2)
        self.foot.hide()
        outer.addWidget(self.foot)

    def add_row(self, key: str, label: str, icon: str = "", into=None, foldable: bool = True) -> NavRow:
        r = NavRow(key, label, icon, foldable=foldable)
        (into if into is not None else self.lay).addWidget(r)
        self.rows[key] = r
        return r

    def add_to_foot(self, w: QWidget) -> None:
        self.foot_lay.addWidget(w)
        self.foot.show()

    def select(self, key: str) -> None:
        for k, r in self.rows.items():
            r.set_current(k == key)

    def recolor(self) -> None:
        for r in self.rows.values():
            r.recolor()


class RecordPager(QFrame):
    """‹ 12 / 38 ›: the record before or after this one, in the list as it's shown (its search, filters, sort and
    folds). A glass capsule floating at the foot of the record; ← and → step too, unless a field has the keys."""

    step = Signal(int)  # -1 or +1

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("Pager")
        lay = hbox(self, tokens.SPACE_1, tokens.SPACE_0_5)
        self.prev = circle_button("chevron-left", "Previous (←)")
        self.next = circle_button("chevron-right", "Next (→)")
        self.where = QLabel()
        self.where.setObjectName("PagerText")
        self.where.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.where.setMinimumWidth(tokens.PAGER_TEXT_W)
        theme.use_tabular(self.where)
        for w in (self.prev, self.where, self.next):
            lay.addWidget(w)
        for b in (self.prev, self.next):
            b.setProperty("bar", True)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # ← and → are its keys
        self.prev.clicked.connect(lambda: self.step.emit(-1))
        self.next.clicked.connect(lambda: self.step.emit(1))
        self.shadow = QGraphicsDropShadowEffect(self)  # it floats: a soft shadow lifts it off the record
        self.shadow.setBlurRadius(tokens.PAGER_SHADOW)
        self.shadow.setOffset(0, tokens.GLASS_SHADOW_DROP)
        self.setGraphicsEffect(self.shadow)
        self.hide()

    def show_at(self, n: int, total: int) -> None:
        """Record n (from 1) of total."""
        self.where.setText(f"{n:,} / {total:,}")
        self.where.setAccessibleName(f"{n:,} of {total:,}")
        self.prev.setEnabled(n > 1)
        self.next.setEnabled(n < total)
        self.shadow.setColor(theme.qcolor(tokens.GLASS_SHADOW))  # (light or dark, as it is now)
        self.adjustSize()
        self.show()
        self.raise_()


class SidePanel(QFrame):
    """A panel on the right. `more`: a ⋯ menu in the header (`more_menu`); `scroll`: the body scrolls.
    `pager`: a RecordPager floats at its foot while a record from a list is open (set_pager)."""

    close_wanted = Signal()  # its round ✕

    def __init__(
        self, title: str, more: bool = False, scroll: bool = True, pager: bool = False, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.setObjectName("Details")
        self.setFixedWidth(tokens.INSPECTOR_W)
        outer = vbox(self, 0, 0)
        self.header = PanelHeader(title)
        self.header.setFixedHeight(tokens.TOOLBAR_H)  # lines up with the table's toolbar
        self.more_menu: QMenu | None = None
        self.more: QToolButton | None = None
        if more:
            self.more_menu = QMenu(self)
            self.more = circle_button("more", "More")
            self.more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            self.more.setMenu(self.more_menu)
            self.header.actions.addWidget(self.more)
        self.close_btn = self.header.add_close()
        self.close_btn.clicked.connect(self.close_wanted.emit)
        outer.addWidget(self.header)
        body = QWidget()
        pad = tokens.SPACE_4
        if scroll:
            self.lay = vbox(body, (pad, pad, pad - tokens.SCROLL_GUTTER, pad), tokens.SPACE_3)
            self.scroll = FitScroll()
            self.scroll.setWidget(body)
            outer.addWidget(self.scroll, 1)
        else:
            self.lay = vbox(body, (pad, 0, pad, pad), tokens.SPACE_3)
            self.scroll = None
            outer.addWidget(body, 1)
        self.footer = QFrame()
        self.footer.setObjectName("PanelFoot")
        self.footer_lay = hbox(self.footer, tokens.SPACE_4, tokens.SPACE_2)
        self.footer.hide()
        outer.addWidget(self.footer)
        self._pad = pad
        self.pager = RecordPager(self) if pager else None
        if self.pager is not None and self.scroll is not None:
            self.scroll.installEventFilter(self)  # ← → reach it from anything that doesn't take them

    def set_pager(self, n: int, total: int) -> None:
        """Show ‹ n / total › (n from 1), or hide it (n 0, or a list of one)."""
        if self.pager is None:
            return
        on = n > 0 and total > 1
        if on:
            self.pager.show_at(n, total)
            self._place_pager()
        else:
            self.pager.hide()
        room = self.pager.sizeHint().height() + 2 * tokens.PAGER_LIFT if on else 0  # the record scrolls clear of it
        m = self.lay.contentsMargins()
        self.lay.setContentsMargins(m.left(), m.top(), m.right(), self._pad + room)

    def _place_pager(self) -> None:
        p = self.pager
        if p is None or p.isHidden():
            return
        foot = self.footer.geometry().top() if self.footer.isVisible() else self.height()
        p.move((self.width() - p.width()) // 2, foot - p.height() - tokens.PAGER_LIFT)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._place_pager()

    def eventFilter(self, obj, e):
        if (
            self.pager is not None
            and self.pager.isVisible()
            and e.type() == QEvent.Type.KeyPress
            and e.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right)
            and not e.modifiers()
        ):
            b = self.pager.prev if e.key() == Qt.Key.Key_Left else self.pager.next
            if b.isEnabled():
                b.click()
            return True
        return super().eventFilter(obj, e)

    def to_top(self) -> None:
        """Back to the top (something else opened in it)."""
        if self.scroll is not None:
            self.scroll.verticalScrollBar().setValue(0)

    def header_icon(self, icon: str, tip: str) -> QToolButton:
        """A round button in the header, before the ⋯ and the ✕."""
        b = circle_button(icon, tip)
        self.header.actions.insertWidget(0, b)
        return b

    def footer_button(self, text: str, icon: str = "", primary: bool = True) -> QPushButton:
        """The panel's next step (Rent This, Agreement…), across the bottom, with its icon: the light raised
        capsule (`primary` is kept for the callers; the standard gives the accent only to +)."""
        b = QPushButton(text)
        b.setObjectName("Raised")  # a record's next step: raised, never the accent (only + is)
        if icon:
            b.setIcon(theme.icon(icon, theme.TEXT, tokens.ICON_SM))
        self.footer_lay.addWidget(b, 1)
        return b
