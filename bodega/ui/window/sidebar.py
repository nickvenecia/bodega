"""The sidebar: where you are. Inventory (All Gear with its groups under it, Kits with each kit), Rentals.
The arrow beside All Gear or Kits folds what's under it; clicking a heading folds the whole section.

Each row shows a count. Import and the tools menu (⋯) sit at the bottom.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QToolButton, QWidget

from bodega.core import dates, pricing
from bodega.core.store import Library
from bodega.ui.components.panels import LeftPanel, NavRow
from bodega.ui.components.widgets import (
    ElidedLabel,
    IconLabel,
    hbox,
    section_label,
    vbox,
)
from bodega.ui.style import theme, tokens

FOLDED_AT_FIRST = ("gear", "rentals")  # rows whose lists start tucked away


class SectionHead(QFrame):
    """A heading over a list in the sidebar. Click it to fold the list away (or bring it back)."""

    toggled = Signal(bool)  # folded

    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("NavHead")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.folded = False
        self.lay = hbox(self, (tokens.SPACE_2, tokens.SPACE_1, 0, tokens.SPACE_1), tokens.SPACE_1)
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
        self._draw()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.set_folded(not self.folded)
            self.toggled.emit(self.folded)
        super().mousePressEvent(e)


class ProfileCard(QFrame):
    """The bottom of the sidebar: your business (its initials, its name) and your account. Click for your
    profiles and Settings."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ProfileCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(tokens.PROFILE_CARD_H)
        lay = hbox(self, (tokens.SPACE_2, 0, tokens.SPACE_2, 0), tokens.SPACE_2)
        self.avatar = QLabel()
        self.avatar.setObjectName("Avatar")
        self.avatar.setFixedSize(tokens.AVATAR, tokens.AVATAR)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.avatar)
        texts = vbox(spacing=0)
        self.name = ElidedLabel()
        self.name.setObjectName("ProfileName")
        self.sub = ElidedLabel()
        self.sub.setObjectName("ProfileSub")
        texts.addWidget(self.name)
        texts.addWidget(self.sub)
        lay.addLayout(texts, 1)
        lay.addWidget(IconLabel("updown", "FAINT"))

    def show_who(self, name: str, sub: str) -> None:
        words = [w for w in name.replace("&", " ").split() if w[:1].isalnum()]
        self.avatar.setText("".join(w[0] for w in words[:2]).upper() or "B")
        self.name.set_full_text(name)
        self.sub.set_full_text(sub)
        self.setToolTip("Profiles and Settings")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class Sidebar(LeftPanel):
    picked = Signal(str)  # "gear", "grp:Lenses", "kits", "out", "upcoming", "rentals", "calendar"
    menu_wanted = Signal(str, QPoint)  # right-click on a place (departments have Rename, Move, Delete)
    dropped = Signal(str)  # gear dropped on a place
    new_group = Signal()
    new_rental = Signal()

    def __init__(self, lib: Library, parent: QWidget | None = None):
        super().__init__(tokens.SIDEBAR_W, tokens.TOOLBAR_H, parent)
        self.lib = lib
        self.current = "gear"
        self.word = word = QLabel(theme.wordmark())
        word.setObjectName("Wordmark")
        word.setTextFormat(Qt.TextFormat.RichText)
        self.top_lay.addWidget(word)

        self.heads: dict[str, SectionHead] = {}
        self.boxes: dict[str, QWidget] = {}  # what folds: a section's list, or the rows under a row
        # each section's + makes something new in it (the window gives Inventory's its menu: gear, group, kit)
        self.btn_new_dep = self._plus("New gear, group or kit")
        inv = self._section("inventory", "Inventory", self.btn_new_dep)
        self._row("gear", "All Gear", "box", inv)
        self.dep_lay = self._under("gear", inv)
        self._row("kits", "Kits", "case", inv)
        self.kit_lay = self._under("kits", inv)
        self.btn_new_rental = self._plus("New Rental")
        self.btn_new_rental.clicked.connect(self.new_rental.emit)
        rent = self._section("rental-section", "Rentals", self.btn_new_rental)
        self._row("rentals", "All Rentals", "receipt", rent)
        under = self._under("rentals", rent)  # what's out, what's coming: views of the same list
        for key, label in (("out", "Out Now"), ("upcoming", "Coming Up")):
            self._row(key, label, "", under).as_child()
        self._row("calendar", "Calendar", "calendar", rent)  # a different view (a timeline), so its own row
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

    @staticmethod
    def _plus(tip: str) -> QToolButton:
        b = QToolButton()
        b.setObjectName("ChipRound")
        b.setIcon(theme.icon("plus", theme.ACCENT, tokens.ICON_SM))
        b.setToolTip(tip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        return b

    def _section(self, key: str, text: str, extra: QWidget | None = None):
        """A heading and the list under it; returns the list's layout."""
        head = SectionHead(text)
        if extra is not None:
            head.lay.addWidget(extra)
        box = QWidget()
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
        b = lib.businesses.get(lib.settings.get("business", "")) or next(iter(lib.businesses.values()), None)
        who = account.current()
        self.profile_card.show_who(
            (b.name if b and b.name else "Your Profile"), who.email if who else "Not signed in"
        )

    def recolor(self) -> None:
        """The look changed: redraw the icons."""
        for h in self.heads.values():
            h._draw()
        for r in self.rows.values():
            r.recolor()
        for b in (self.btn_new_dep, self.btn_new_rental):
            b.setIcon(theme.icon("plus", theme.ACCENT, tokens.ICON_SM))

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
            row.label.setText(k.name or "Untitled Kit")
        self.rows["gear"].arrow.setVisible(bool(groups))
        self.rows["kits"].arrow.setVisible(bool(kits))
        self.rows["rentals"].arrow.setVisible(True)
        self.rows["gear"].set_count(len(lib.items))
        for g in groups:
            self.rows[f"grp:{g}"].set_count(sum(1 for i in lib.items.values() if i.group == g))
        self.rows["kits"].set_count(len(lib.packages))
        self.show_who()
        rentals = list(lib.rentals.values())
        out = [r for r in rentals if r.status == "out"]
        late = any(pricing.late(r) for r in out)
        self.rows["out"].set_count(len(out), "late" if late else ("out" if out else ""))
        today = dates.iso(dates.today())
        self.rows["upcoming"].set_count(
            sum(
                1 for r in rentals if r.status in ("quote", "booked") and (r.return_date or r.pickup) >= today
            )
        )
        # folded, All Rentals still shows when something's out (amber) or late (red)
        tone = ("late" if late else ("out" if out else "")) if self.rows["rentals"].folded else ""
        self.rows["rentals"].set_count(len(rentals), tone)
        self.select(
            self.current
            if self.current in self.rows
            else ("kits" if self.current.startswith("kit:") else "gear")
        )
