"""What the main window's parts share: the places (PLACES: the sidebar, the View menu and the page titles all
read it), the gear filters, kind_of()."""

from __future__ import annotations

from dataclasses import dataclass

from bodega.core.log import get_logger

log = get_logger(__name__)


GEAR_FILTERS = [
    ("all", "All Gear", ""),
    ("in", "In", "Not out, not in repair"),
    ("out", "Out", "On a rental that's out"),
    ("repair", "In Repair", ""),
    ("rentable", "For Rent", ""),
]


@dataclass(frozen=True)
class Place:
    """One place in the sidebar. `under`: the row it sits under; `menu`/`keys`: its View menu item."""

    key: str
    title: str
    icon: str = ""
    under: str = ""
    menu: str = ""
    keys: str = ""


PLACES = (  # in the sidebar's order (each group's own places, like Lenses, come from your gear)
    Place("gear", "All Gear", "box", menu="All Gear", keys="Ctrl+1"),
    Place("kits", "Kits", "case", menu="Kits", keys="Ctrl+2"),
    Place("rentals", "All Rentals", "receipt", menu="Rentals", keys="Ctrl+3"),
    Place("out", "Out Now", under="rentals"),
    Place("upcoming", "Coming Up", under="rentals"),
    Place("calendar", "Calendar", "calendar", menu="Calendar", keys="Ctrl+4"),
)
PLACE = {p.key: p for p in PLACES}
TITLES = {p.key: p.title for p in PLACES}
PAGE_DOCS = {
    "rental": [("agreement", "Rental Agreement")],
    "kit": [("package", "Kit Sheet"), ("ratecard", "Rate Card")],
    "gear": [("inventory", "Inventory List"), ("ratecard", "Rate Card"), ("labels", "Labels")],
}


def kind_of(view: str) -> str:
    """What a sidebar place shows: gear, kits or rentals."""
    if view == "gear" or view.startswith("grp:"):
        return "gear"
    if view == "kits":
        return "packages"
    return "rentals"
