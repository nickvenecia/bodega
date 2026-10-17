"""How a page prints (the standard's C-53 and C-61): its paper, whether it carries your letterhead, a note at its foot,
and on a list (the inventory, the rate card) which columns in which order and which gear (filters). Kept as you last
chose them for each kind of page (settings "page_options"), and as a profile's default (Business.page_options) for
a page you haven't set yet. No Qt here: the page window shows these, the documents (core/document.py) use them.

A filter is one column and what it keeps: for a figure (what it cost, a day's rate, how many) a range, From and To,
read however it's typed ("$1,200", "1200"); for words (a group, a company, a status) the one value."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bodega.core import money, pricing
from bodega.core.model import ITEM_WORDS, Business, Item

PAPERS = {"letter": ("Letter", (612.0, 792.0)), "a4": ("A4", (595.28, 841.89))}
NOTE_MAX = 400  # a note at the foot of a page: a line or two

# a list's columns: key -> (heading, its share of the width, alignment); the first are shown at first, in this order
INVENTORY_COLUMNS = {
    "qty": ("Qty", 0.07, "center"),
    "gear": ("Gear", 0.47, "left"),
    "serials": ("Serial Numbers", 0.18, "left"),
    "value": ("Unit Value", 0.13, "right"),
    "total": ("Total", 0.15, "right"),
    "company": ("Company", 0.14, "left"),
    "group": ("Group", 0.14, "left"),
    "day": ("Day Rate", 0.11, "right"),
    "status": ("Status", 0.11, "left"),
}
INVENTORY_SHOWN = ["qty", "gear", "serials", "value", "total"]
RATECARD_COLUMNS = {
    "gear": ("Gear", 0.68, "left"),
    "day": ("Day", 0.16, "right"),
    "week": ("Week", 0.16, "right"),
    "company": ("Company", 0.18, "left"),
    "value": ("Replacement Value", 0.18, "right"),
}
RATECARD_SHOWN = ["gear", "day", "week"]
COLUMNS = {"inventory": (INVENTORY_COLUMNS, INVENTORY_SHOWN), "ratecard": (RATECARD_COLUMNS, RATECARD_SHOWN)}
NAME_COLUMN = "gear"  # always shown: what each row is

# what a list can be filtered by: key -> (its name, "range" for a figure or "one" for words)
FILTERS = {
    "group": ("Group", "one"),
    "company": ("Company", "one"),
    "status": ("Status", "one"),
    "value": ("Paid Each", "range"),
    "day": ("Day Rate", "range"),
    "qty": ("How Many", "range"),
}


@dataclass
class Filter:
    col: str = "group"
    lo: str = ""  # From (a figure), or the value (words)
    hi: str = ""  # To (a figure)

    @classmethod
    def from_dict(cls, d) -> Filter | None:
        if not isinstance(d, dict) or d.get("col") not in FILTERS:
            return None
        return cls(str(d["col"]), str(d.get("lo") or "")[:80], str(d.get("hi") or "")[:80])

    def to_dict(self) -> dict:
        return {"col": self.col, "lo": self.lo, "hi": self.hi}

    @property
    def label(self) -> str:
        return FILTERS[self.col][0]

    @property
    def is_range(self) -> bool:
        return FILTERS[self.col][1] == "range"


@dataclass
class PageOptions:
    paper: str = "letter"
    letterhead: bool = True  # your logo, name and contact at the top
    note: str = ""  # printed at the foot
    columns: list[str] | None = None  # a list's columns, in order (None: its own)
    filters: list[Filter] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d) -> PageOptions:
        """Read safely: anything odd is left as the default (a hand-edited file, an older Bodega)."""
        if not isinstance(d, dict):
            return cls()
        o = cls()
        if d.get("paper") in PAPERS:
            o.paper = d["paper"]
        if isinstance(d.get("letterhead"), bool):
            o.letterhead = d["letterhead"]
        if isinstance(d.get("note"), str):
            o.note = d["note"][:NOTE_MAX]
        cols = d.get("columns")
        if isinstance(cols, list) and all(isinstance(c, str) for c in cols):
            o.columns = list(dict.fromkeys(cols))
        if isinstance(d.get("filters"), list):
            o.filters = [f for f in (Filter.from_dict(x) for x in d["filters"]) if f is not None]
        return o

    def to_dict(self) -> dict:
        return {
            "paper": self.paper,
            "letterhead": self.letterhead,
            "note": self.note,
            "columns": self.columns,
            "filters": [f.to_dict() for f in self.filters],
        }

    @property
    def size(self) -> tuple[float, float]:
        return PAPERS.get(self.paper, PAPERS["letter"])[1]


def for_page(settings: dict, b: Business | None, kind: str) -> PageOptions:
    """The options a page opens with: as you last chose them for this kind, else your profile's default."""
    kept = settings.get("page_options")
    if isinstance(kept, dict) and kind in kept:
        return PageOptions.from_dict(kept[kind])
    if b is not None and isinstance(b.page_options, dict) and kind in b.page_options:
        return PageOptions.from_dict(b.page_options[kind])
    return PageOptions()


def remember(settings: dict, kind: str, o: PageOptions) -> None:
    kept = settings.get("page_options")
    kept = dict(kept) if isinstance(kept, dict) else {}
    kept[kind] = o.to_dict()
    settings["page_options"] = kept


def columns(kind: str, o: PageOptions) -> list[str]:
    """A list's columns to show, in order: yours (only the ones it has, its name always among them), else its own."""
    known, shown = COLUMNS[kind]
    picked = [c for c in (o.columns or shown) if c in known]
    if NAME_COLUMN not in picked:
        picked.insert(0, NAME_COLUMN)
    return picked


def reading_key(text: str) -> list:
    """Words and numbers in reading order: "INV-9" before "INV-10", "lens 2" before "Lens 10"."""
    return [(0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.findall(r"\d+|\D+", text.casefold())]


def values(items: list[Item], col: str) -> list[str]:
    """The values a words filter can keep, in reading order."""
    got = {_words(it, col) for it in items} - {""}
    return sorted(got, key=reading_key)


def _words(it: Item, col: str) -> str:
    if col == "group":
        return it.group or "Other"
    if col == "company":
        return it.brand
    if col == "status":
        return ITEM_WORDS.get(it.status, it.status)
    return ""


def _figure(lib, it: Item, col: str, b: Business | None):
    if col == "value":
        return money.parse(it.value)
    if col == "day":
        return pricing.item_rate(lib, it, b)
    return money.parse(str(it.qty))


def keeps(lib, it: Item, f: Filter, b: Business | None) -> bool:
    """Whether `it` is kept by the filter (one with nothing typed keeps everything)."""
    if not f.is_range:
        return not f.lo or _words(it, f.col) == f.lo
    v = _figure(lib, it, f.col, b)
    lo, hi = money.parse(f.lo) if f.lo.strip() else None, money.parse(f.hi) if f.hi.strip() else None
    return (lo is None or v >= lo) and (hi is None or v <= hi)


def kept(lib, items: list[Item], o: PageOptions, b: Business | None) -> list[Item]:
    """The gear every filter keeps."""
    return [it for it in items if all(keeps(lib, it, f, b) for f in o.filters)]
