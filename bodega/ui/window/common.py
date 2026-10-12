"""What the main window's parts share: timings, the gear filters, page titles, kind_of()."""

from __future__ import annotations

from bodega.core.log import get_logger

log = get_logger(__name__)


GEAR_FILTERS = [
    ("all", "Everything", ""),
    ("in", "In", "Not out, not in repair"),
    ("out", "Out", "On a rental that's out"),
    ("repair", "In Repair", ""),
    ("rentable", "For Rent", ""),
]
TITLES = {
    "gear": "All Gear",
    "kits": "Kits",
    "out": "Out Now",
    "upcoming": "Coming Up",
    "rentals": "All Rentals",
    "calendar": "Calendar",
}
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
