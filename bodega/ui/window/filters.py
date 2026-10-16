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

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QLabel, QMenu, QToolButton, QWidgetAction

from bodega.core import maintenance, money, pricing
from bodega.ui.style import theme

DIVIDES = [("group", "Group"), ("brand", "Company"), ("none", "No Dividers")]
SHOWS = [
    ("all", "Everything", ""),
    ("in", "In", "On the shelf: not out, not in repair"),
    ("out", "Out", "On a rental that's out now"),
    ("booked", "Booked", "On a booked rental that hasn't gone out yet"),
    ("repair", "In Repair", ""),
    ("retired", "Retired", ""),
    ("service", "Needs Service", "Due for service in the next two weeks, or overdue"),
    ("rentable", "For Rent", ""),
    ("private", "Not For Rent", ""),
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

    # ------------------------------------------------------------------ state
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

    # ------------------------------------------------------------------ the menu
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
        self._choices(co, "company", [("", "Any Company")] + [(n, n) for n in names], self.filter.company)
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
