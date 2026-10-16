"""The gear list's filter button: how the list is divided, and which gear it shows.

    Divide By    Group / Company / No Dividers
    Show         Everything / In / Out / Booked / In Repair / Retired / For Rent / Not For Rent
    Company   ▸  any one company
    Missing   ▸  Link, Price, Serial Numbers, Company (any you tick)
    Clear Filters

Just an icon; the accent while a filter hides gear. Clear Filters puts everything back to how it starts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QLabel, QMenu, QPushButton, QToolButton, QWidget, QWidgetAction

from bodega.core import maintenance, money, pricing
from bodega.ui.components.widgets import hbox
from bodega.ui.style import theme, tokens

DIVIDES = [("group", "Group"), ("brand", "Company"), ("none", "No Dividers")]
SHOWS = [
    ("all", "All Gear", ""),
    ("in", "In", "On the shelf: not out, not in repair"),
    ("out", "Out", "On a rental that's out now"),
    ("booked", "Booked", "On a booked rental that hasn't gone out yet"),
    ("repair", "In Repair", ""),
    ("retired", "Retired", ""),
    ("service", "Needs Service", "Due for service in the next two weeks, or overdue"),
    ("rentable", "For Rent", ""),
    ("private", "Not for Rent", ""),
]
MISSING = [
    ("link", "Link"),
    ("price", "Price"),
    ("serials", "Serial Numbers"),
    ("brand", "Company"),
]
SHOW_LABEL = {k: label for k, label, _t in SHOWS}


@dataclass
class GearFilter:
    show: str = "all"
    company: str = ""  # "" = any
    missing: set[str] = field(default_factory=set)

    def active(self) -> bool:
        return self.show != "all" or bool(self.company) or bool(self.missing)

    def summary(self) -> str:
        parts = []
        if self.show != "all":
            parts.append(SHOW_LABEL.get(self.show, ""))
        if self.company:
            parts.append(self.company)
        if self.missing:
            names = dict(MISSING)
            parts.append("No " + ", ".join(names[k] for k, _l in MISSING if k in self.missing))
        return " · ".join(parts)

    def keep(self, lib):
        """A test on an item id, or None when nothing's filtered."""
        if not self.active():
            return None
        out = pricing.units_out(lib) if self.show in ("in", "out") else {}
        booked = pricing.booked_ahead(lib) if self.show == "booked" else set()
        show, company, missing = self.show, self.company.casefold(), self.missing

        def keep(item_id: str) -> bool:
            it = lib.items.get(item_id)
            if it is None:
                return False
            n = out.get(it.id, 0)
            ok = {
                "all": True,
                "in": it.status == "ready" and n < it.qty,
                "out": n > 0,
                "booked": it.id in booked,
                "repair": it.status == "repair",
                "retired": it.status == "retired",
                "service": maintenance.needs_service(it),
                "rentable": it.rentable and it.status != "retired",
                "private": not it.rentable,
            }.get(show, True)
            if ok and company:
                ok = it.brand.strip().casefold() == company
            if ok and "link" in missing:
                ok = not it.link.strip()
            if ok and "price" in missing:
                ok = money.parse(it.value) == 0
            if ok and "serials" in missing:
                ok = not any(s.strip() for s in it.serials)
            if ok and "brand" in missing:
                ok = not it.brand.strip()
            return ok

        return keep


class FilterButton(QToolButton):
    """The icon that opens the filter menu (built fresh each time, so Company lists today's companies)."""

    changed = Signal()  # anything picked

    def __init__(self, companies, parent=None):
        super().__init__(parent)
        self.setObjectName("Circle")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.companies = companies  # () -> list of company names
        self.filter = GearFilter()
        self.divide = "group"
        self.default_divide = "group"
        self.m = QMenu(self)
        self.m.setToolTipsVisible(True)
        self.m.aboutToShow.connect(self._build)
        self.setMenu(self.m)
        self.show_state()

    # State
    def set_divide(self, key: str, default: str) -> None:
        self.divide, self.default_divide = key, default

    def is_default(self) -> bool:
        return not self.filter.active() and self.divide == self.default_divide

    def clear(self) -> None:
        self.filter = GearFilter()
        self.divide = self.default_divide
        self.show_state()

    def clear_filter(self) -> None:
        """What's shown back to everything (how it's divided stays: that's kept per place)."""
        self.filter = GearFilter()
        self.show_state()

    def show_state(self) -> None:
        on = self.filter.active()
        self.setIcon(theme.icon("filter", theme.ACCENT if on else theme.MUTED))
        if bool(self.property("active")) != on:
            self.setProperty("active", on)
            self.style().unpolish(self)
            self.style().polish(self)
        self.setToolTip(f"Showing: {self.filter.summary()}" if on else "Filter and divide the list")

    def _pick(self, what: str, key: str, on: bool = True) -> None:
        if what == "divide":
            self.divide = key
        elif what == "show":
            self.filter.show = key
        elif what == "company":
            self.filter.company = key
        elif what == "missing":
            (self.filter.missing.add if on else self.filter.missing.discard)(key)
        self.show_state()
        self.changed.emit()

    # The menu
    def _heading(self, text: str) -> None:
        label = QLabel(text)
        label.setObjectName("MenuHeading")
        a = QWidgetAction(self.m)
        a.setDefaultWidget(label)
        a.setEnabled(False)
        self.m.addAction(a)

    def _choices(self, menu: QMenu, what: str, items, current: str) -> None:
        group = QActionGroup(menu)
        for key, label, *tip in items:
            a = QAction(label, group)
            a.setCheckable(True)
            a.setChecked(key == current)
            if tip and tip[0]:
                a.setToolTip(tip[0])
            a.triggered.connect(lambda _c=False, k=key: self._pick(what, k))
            menu.addAction(a)

    def _build(self) -> None:
        m = self.m
        m.clear()
        self._heading("Divide By")
        self._choices(m, "divide", DIVIDES, self.divide)
        m.addSeparator()
        self._heading("Show")
        self._choices(m, "show", SHOWS, self.filter.show)
        m.addSeparator()
        names = self.companies()
        co = m.addMenu(f"Company: {self.filter.company}" if self.filter.company else "Company")
        self._choices(co, "company", [("", "All Companies")] + [(n, n) for n in names], self.filter.company)
        miss = m.addMenu("Missing")
        for key, label in MISSING:
            a = miss.addAction(f"No {label}")
            a.setCheckable(True)
            a.setChecked(key in self.filter.missing)
            a.toggled.connect(lambda on, k=key: self._pick("missing", k, on))
        m.addSeparator()
        clear = m.addAction("Clear Filters")
        clear.setEnabled(not self.is_default())
        clear.triggered.connect(self._clear)

    def _clear(self) -> None:
        self.clear()
        self.changed.emit()


class FilterChips(QWidget):
    """Under the bar while a filter hides gear: one capsule for each ("Out", "Sony", "No Link"), with an ✕ that
    takes it off. A chip acts once its click is over: taking a filter off rebuilds the chips."""

    removed = Signal(str, str)  # what kind ("show", "company", "missing"), which

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.lay = hbox(self, (tokens.PAGE_INSET, 0, tokens.PAGE_INSET, tokens.SPACE_2), tokens.SPACE_2)
        self.lay.addStretch(1)
        self.chips: list[QPushButton] = []
        self.hide()

    def show_for(self, f: GearFilter | None) -> None:
        on = []
        if f is not None:
            if f.show != "all":
                on.append(("show", f.show, SHOW_LABEL.get(f.show, f.show)))
            if f.company:
                on.append(("company", f.company, f.company))
            on += [("missing", k, f"No {label}") for k, label in MISSING if k in f.missing]
        if [c.text() for c in self.chips] == [label for _w, _k, label in on]:
            self.setVisible(bool(on))
            return
        for c in self.chips:  # hidden first, then thrown away (one may still be finishing its click)
            c.hide()
            c.deleteLater()
        self.chips = []
        for n, (what, key, label) in enumerate(on):
            b = QPushButton(label)
            b.setObjectName("FilterChip")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setLayoutDirection(Qt.LayoutDirection.RightToLeft)  # the ✕ after the words
            b.setIcon(theme.icon("x", theme.MUTED, tokens.ICON_SM))
            b.setToolTip("Take this filter off")
            b.setAccessibleName(f"Remove filter {label}")
            b.clicked.connect(
                lambda _c=False, w=what, k=key: QTimer.singleShot(0, self, lambda: self.removed.emit(w, k))
            )
            self.lay.insertWidget(n, b)
            self.chips.append(b)
        self.setVisible(bool(on))
