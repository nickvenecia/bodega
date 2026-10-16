"""What the main window's parts share: the places (PLACES: the sidebar, the View menu and the page titles all
read it), the page window's pages (PAGES), the gear filters, kind_of()."""

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


@dataclass(frozen=True)
class PageDoc:
    """One page the page window can show. `build`: the window's method that makes it, from what it's of (a
    rental's, a kit's or a group's id) to (the page, whose it is, its file name), or None if that's gone."""

    key: str
    label: str
    build: str


@dataclass(frozen=True)
class PageKind:
    """The pages for one kind of thing, the first shown first. `rental`: the rental's own tools are there
    (Mark as Booked, Email Renter) and its title names it."""

    docs: tuple[PageDoc, ...]
    rental: bool = False

    def choices(self) -> list[tuple[str, str]]:
        return [(d.key, d.label) for d in self.docs]

    def doc(self, key: str) -> PageDoc:
        return next((d for d in self.docs if d.key == key), self.docs[0])


RATE_CARD = PageDoc("ratecard", "Rate Card", "_rate_card")
PAGES = {  # what the page window shows, by what it was opened for
    "rental": PageKind((PageDoc("agreement", "Rental Agreement", "_agreement"),), rental=True),
    "kit": PageKind((PageDoc("package", "Kit Sheet", "_kit_sheet"), RATE_CARD)),
    "gear": PageKind(
        (PageDoc("inventory", "Inventory List", "_inventory"), RATE_CARD, PageDoc("labels", "Labels", "_labels"))
    ),
}


def kind_of(view: str) -> str:
    """What a sidebar place shows: gear, kits or rentals."""
    if view == "gear" or view.startswith("grp:"):
        return "gear"
    if view == "kits":
        return "packages"
    return "rentals"
