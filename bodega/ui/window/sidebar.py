"""The sidebar: where you are. Inventory (All Gear with its groups under it, Kits with each kit), Rentals.
The arrow beside All Gear or Kits folds what's under it; clicking a heading folds the whole section.

Each row shows a count. Import and the tools menu (⋯) sit at the bottom.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QKeySequence
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QLabel, QPushButton, QToolButton, QWidget

from bodega.core import pricing, settings
from bodega.core.store import Library
from bodega.ui.components.panels import LeftPanel, NavRow
from bodega.ui.components.widgets import (
    ElidedLabel,
    IconLabel,
    by_keyboard,
    hbox,
    repolish,
    section_label,
    vbox,
)
from bodega.ui.style import theme, tokens
from bodega.ui.window.common import PLACE, PLACES

FOLDED_AT_FIRST = ("gear", "rentals")  # rows whose lists start tucked away


class SectionHead(QFrame):
    """A heading over a list in the sidebar. Click it to fold the list away (or bring it back)."""

    toggled = Signal(bool)  # folded

    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("NavHead")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)  # Tab reaches it; Return or Space folds it
        self.setAccessibleName(text)
        self.folded = False
        self.lay = hbox(self, (tokens.SPACE_2, tokens.SPACE_1, tokens.SPACE_1, tokens.SPACE_1), tokens.SPACE_1)
        self.label = section_label(text)
        self.chevron = IconLabel("chevron", "FAINT")
        self.lay.addWidget(self.label)
        self.lay.addWidget(self.chevron)
        self.lay.addStretch(1)
        self.setFixedHeight(tokens.NAV_H)
        self._draw()

    def _draw(self) -> None:
        self.chevron.set_icon("chevron-right" if self.folded else "chevron")

    def set_folded(self, on: bool) -> None:
        self.folded = on
        self.setAccessibleDescription("Collapsed" if on else "Expanded")
        self._draw()

    def _fold(self) -> None:
        self.set_folded(not self.folded)
        self.toggled.emit(self.folded)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._fold()
        super().mousePressEvent(e)

    def keyPressEvent(self, e):
        if not by_keyboard(self, self._fold, e):
            super().keyPressEvent(e)


class ProfileCard(QFrame):
    """The bottom of the sidebar: your business (its initials, its name), and your account's email once you're
    signed in. Click for your profiles, feedback, updates and Settings."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ProfileCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)  # Tab reaches it; Return or Space opens its menu
        self.setFixedHeight(tokens.PROFILE_CARD_H)
        lay = hbox(self, (tokens.SPACE_2, 0, tokens.SPACE_2, 0), tokens.SPACE_2)
        self.avatar = QLabel()
        self.avatar.setObjectName("Avatar")
        self.avatar.setFixedSize(tokens.MONOGRAM, tokens.MONOGRAM)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.avatar)
        texts = vbox(
            spacing=0
        )  # the name (and who's signed in, when someone is), tight and centred like the App Store's
        self.name = ElidedLabel()
        self.name.setObjectName("ProfileName")
        self.sub = ElidedLabel()
        self.sub.setObjectName("ProfileSub")
        texts.addStretch(1)
        texts.addWidget(self.name)
        texts.addWidget(self.sub)
        texts.addStretch(1)
        lay.addLayout(texts, 1)
        lay.addWidget(IconLabel("updown", "FAINT"))

    def show_who(self, name: str, sub: str, problem: bool = False) -> None:
        """`problem`: `sub` says what's wrong (Not Saved), in color."""
        words = [w for w in name.replace("&", " ").split() if w[:1].isalnum()]
        self.avatar.setText("".join(w[0] for w in words[:2]).upper() or "B")
        self.name.set_full_text(name)
        self.sub.set_full_text(sub)
        self.sub.setVisible(bool(sub))  # nothing to say until someone's signed in, or something's wrong
        tone = "problem" if problem else ""
        if self.sub.property("tone") != tone:
            self.sub.setProperty("tone", tone)
            repolish(self.sub)
        self.setToolTip(
            "Profiles and Settings · Your latest changes aren't saved"
            if problem
            else "Profiles and Settings · Saved on this computer"
        )
        self.setAccessibleName(f"{name}, Profiles and Settings")
        self.setAccessibleDescription(sub)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            QTimer.singleShot(0, self, self.clicked.emit)  # once the key is over
            return
        super().keyPressEvent(e)


class Sidebar(LeftPanel):
    picked = Signal(str)  # "gear", "grp:Lenses", "kits", "out", "upcoming", "rentals", "calendar"
    menu_wanted = Signal(str, QPoint)  # right-click on a place (departments have Rename, Move, Delete)
    dropped = Signal(str)  # gear dropped on a place
    new_group = Signal()
    new_rental = Signal()
    search_wanted = Signal()  # the Search capsule at the top: Search Everything (⌘K)

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(tokens.SIDEBAR_W, tokens.TOOLBAR_H, parent)
        self.lib = lib
        self.current = "gear"
        self.word = word = QLabel(theme.wordmark())
        word.setObjectName("Wordmark")
        word.setTextFormat(Qt.TextFormat.RichText)
        self.top_lay.addWidget(word)

        # at the top, as a Mac's sidebar has it: Search, for the whole of Bodega (⌘K)
        keys = QKeySequence("Ctrl+K").toString(QKeySequence.SequenceFormat.NativeText)
        self.search = QPushButton("Search")
        self.search.setObjectName("SideSearch")
        self.search.setIcon(theme.icon("search", theme.MUTED, tokens.ICON))
        self.search.setToolTip(f"Search Everything ({keys})")
        self.search.setAccessibleName("Search Everything")
        self.search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search.clicked.connect(
            lambda: QTimer.singleShot(0, self, self.search_wanted.emit)
        )  # once the click is over
        self.lay.addWidget(self.search)
        self.lay.addSpacing(tokens.SPACE_2)

        self.heads: dict[str, SectionHead] = {}
        self.boxes: dict[str, QWidget] = {}  # what folds: a section's list, or the rows under a row
        # each section's + makes something new in it (the window gives Inventory's its menu: gear, group, kit)
        self.btn_new_dep = self._plus("New Gear, Group or Kit")
        inv = self._section("inventory", "Inventory", self.btn_new_dep)
        self._place("gear", inv)
        self.dep_lay = self._under("gear", inv)
        self._place("kits", inv)
        self.kit_lay = self._under("kits", inv)
        self.btn_new_rental = self._plus("New Rental")
        self.btn_new_rental.clicked.connect(self.new_rental.emit)
        rent = self._section("rental-section", "Rentals", self.btn_new_rental)
        self._place("rentals", rent)
        under = self._under("rentals", rent)  # what's out, what's coming: views of the same list
        for p in PLACES:
            if p.under == "rentals":
                self._place(p.key, under).as_child()
        self._place("calendar", rent)  # a different view (a timeline), so its own row
        self.lay.addStretch(1)
        folded = lib.settings.get("sidebar_folded", list(FOLDED_AT_FIRST))
        if not isinstance(folded, list):
            folded = list(FOLDED_AT_FIRST)
        # rows added since your folds were saved start folded too (once; after that it's your choice)
        seen = lib.settings.get("sidebar_rows_seen")
        seen = set(seen) if isinstance(seen, list) else {"gear", "kits"}
        folded += [k for k in FOLDED_AT_FIRST if k not in seen and k not in folded]
        lib.settings["sidebar_rows_seen"] = sorted(seen | set(FOLDED_AT_FIRST) | {"kits"})
        lib.settings["sidebar_folded"] = sorted(set(folded))
        for key in folded:
            if key in self.boxes:
                self._show_fold(key, True)

        self.btn_update = QPushButton()
        self.add_to_foot(self.btn_update)
        self.btn_update.hide()
        self.profile_card = ProfileCard()  # your profiles, and Settings (⌘,)
        self.add_to_foot(self.profile_card)
        self.refresh()

    def _plus(self, tip: str) -> QToolButton:
        """A section's add button, as on the Mac: a small plain gray +, faded in while the pointer is over its
        own section (heading or rows) and faded out when it leaves. Always there for the layout, so nothing shifts."""
        b = QToolButton()
        b.setObjectName("SectionAdd")
        b.setIcon(theme.icon("plus", theme.MUTED, tokens.ICON_SM))
        b.setToolTip(tip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # the same commands are in the menus, with keys
        fx = QGraphicsOpacityEffect(b)
        fx.setOpacity(0.0)
        b.setGraphicsEffect(fx)
        anim = QPropertyAnimation(fx, b"opacity", b)
        anim.setDuration(tokens.FADE_MS)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        b._fade = anim
        return b

    @staticmethod
    def _fade(b: QToolButton, on: bool) -> None:
        fx, anim = b.graphicsEffect(), b._fade
        target = 1.0 if on else 0.0
        if anim.endValue() == target and anim.state() == QPropertyAnimation.State.Running:
            return
        if abs(fx.opacity() - target) < 0.01:
            return
        anim.stop()
        anim.setStartValue(fx.opacity())
        anim.setEndValue(target)
        anim.start()

    def _hover_check(self) -> None:
        """Show the + of the section under the pointer, and only that one."""
        at = QCursor.pos()
        for key, plus in getattr(self, "_section_plus", {}).items():
            head, box = self.heads[key], self.boxes[key]
            area = QRect(head.mapToGlobal(QPoint(0, 0)), head.size())
            if box.isVisible():
                area = area.united(QRect(box.mapToGlobal(QPoint(0, 0)), box.size()))
            self._fade(plus, self.underMouse() and area.contains(at))

    def eventFilter(self, obj, e):
        if e.type() in (QEvent.Type.Enter, QEvent.Type.Leave, QEvent.Type.HoverMove):
            QTimer.singleShot(0, self._hover_check)
        return super().eventFilter(obj, e)

    def leaveEvent(self, e):
        for plus in getattr(self, "_section_plus", {}).values():
            self._fade(plus, False)
        super().leaveEvent(e)

    def _section(self, key: str, text: str, extra: QWidget | None = None):
        """A heading and the list under it; returns the list's layout."""
        head = SectionHead(text)
        if extra is not None:
            head.lay.addWidget(extra)
        box = QWidget()
        if isinstance(extra, QToolButton) and extra.objectName() == "SectionAdd":
            self._section_plus = {**getattr(self, "_section_plus", {}), key: extra}
            for w in (head, box):
                w.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
                w.installEventFilter(self)
        lay = vbox(box, (0, 0, 0, tokens.SPACE_3), tokens.NAV_GAP)
        head.toggled.connect(lambda folded, k=key: self._fold(k, folded))
        self.lay.addWidget(head)
        self.lay.addWidget(box)
        self.heads[key], self.boxes[key] = head, box
        return lay

    def _under(self, key: str, into):
        """The rows under row `key` (its arrow folds them); returns their layout."""
        box = QWidget()
        lay = vbox(box, 0, tokens.NAV_GAP)
        into.addWidget(box)
        self.boxes[key] = box
        self.rows[key].fold_wanted.connect(lambda k: self._fold(k, not self.rows[k].folded))
        return lay

    def show_who(self) -> None:
        """The profile card: your business, and whether you're signed in."""
        from bodega.services import account

        lib = self.lib
        b = lib.businesses.get(settings.value(lib.settings, "business")) or next(iter(lib.businesses.values()), None)
        who = account.current()
        name = b.name if b and b.name else "Your Profile"
        if lib.unsaved:
            self.profile_card.show_who(name, "Not Saved", problem=True)
        else:
            self.profile_card.show_who(name, who.email if who else "")

    def recolor(self) -> None:
        """The look changed: redraw the icons."""
        for h in self.heads.values():
            h._draw()
        for r in self.rows.values():
            r.recolor()
        for b in (self.btn_new_dep, self.btn_new_rental):
            b.setIcon(theme.icon("plus", theme.MUTED, tokens.ICON_SM))

    def _show_fold(self, key: str, folded: bool) -> None:
        self.boxes[key].setVisible(not folded)
        if key in self.heads:
            self.heads[key].set_folded(folded)
        else:
            self.rows[key].set_folded(folded)

    def _fold(self, key: str, folded: bool) -> None:
        self._show_fold(key, folded)
        self.lib.settings["sidebar_folded"] = sorted(
            [k for k, h in self.heads.items() if h.folded]
            + [k for k in ("gear", "kits", "rentals") if self.rows[k].folded]
        )
        self.lib.save_settings()
        if key == "rentals":
            self.refresh()  # its count shows out / late only while folded

    def _place(self, key: str, into=None) -> NavRow:
        """A row for one of PLACES (window/common.py), with its title and icon from there."""
        p = PLACE[key]
        return self._row(p.key, p.title, p.icon, into)

    def _row(self, key: str, label: str, icon: str = "", into=None) -> NavRow:
        r = self.add_row(key, label, icon, into)
        r.clicked.connect(self.pick)
        r.menu_wanted.connect(self.menu_wanted.emit)
        if key == "gear" or key.startswith("grp:"):
            r.setAcceptDrops(True)
            r.dropped.connect(self.dropped.emit)
        return r

    def pick(self, key: str) -> None:
        self.select(key)
        self.picked.emit(key)

    def select(self, key: str) -> None:
        self.current = key
        super().select(key)

    def refresh(self) -> None:
        """Counts, and one row per group."""
        lib = self.lib
        groups = lib.groups()
        have = [k for k in self.rows if k.startswith("grp:")]
        if have != [f"grp:{g}" for g in groups]:
            for k in have:
                self.rows.pop(k).deleteLater()
            for g in groups:
                r = self._row(f"grp:{g}", g, "", self.dep_lay)
                r.as_child()
        kits = sorted(lib.packages.values(), key=lambda k: (k.name or "").lower())
        have = [k for k in self.rows if k.startswith("kit:")]
        if have != [f"kit:{k.id}" for k in kits]:
            for k in have:
                self.rows.pop(k).deleteLater()
            for k in kits:
                r = self._row(f"kit:{k.id}", "", "", self.kit_lay)
                r.as_child()
        for k in kits:
            row = self.rows[f"kit:{k.id}"]
            row.set_label(k.name or "Untitled Kit")
        self.rows["gear"].arrow.setVisible(bool(groups))
        self.rows["kits"].arrow.setVisible(bool(kits))
        self.rows["rentals"].arrow.setVisible(True)
        self.rows["gear"].set_count(len(lib.items))
        for g in groups:
            self.rows[f"grp:{g}"].set_count(sum(1 for i in lib.items.values() if i.group == g))
        self.rows["kits"].set_count(len(lib.packages))
        self.show_who()
        rentals = list(lib.rentals.values())
        out = [r for r in rentals if r.is_out()]
        late = sum(1 for r in out if pricing.late(r))
        # late says so in words, not only in red ("2 late"): color is never the only sign
        self.rows["out"].set_count(f"{late} late" if late else len(out), "late" if late else ("out" if out else ""))
        self.rows["upcoming"].set_count(sum(1 for r in rentals if pricing.coming_up(r)))
        # folded, All Rentals still shows when something's out (amber) or late (red)
        folded = self.rows["rentals"].folded
        tone = ("late" if late else ("out" if out else "")) if folded else ""
        self.rows["rentals"].set_count(f"{late} late" if late and folded else len(rentals), tone)
        self.select(
            self.current if self.current in self.rows else ("kits" if self.current.startswith("kit:") else "gear")
        )
