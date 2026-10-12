"""Checking a rental's gear out and back in: one row per piece it sends out (attached gear and kits' gear
included), each ticked when it leaves and when it returns, with a note and photos of its condition.
"""

from __future__ import annotations

from bodega.core import pricing
from bodega.core.model import CheckRow, Item, Rental


def pieces(lib, r: Rental) -> list[tuple[Item, int]]:
    """Every piece this rental sends out and how many, in the order of its lines."""
    units: dict[str, int] = {}
    order: list[Item] = []
    for line in r.lines:
        for it, n, _depth in pricing.line_gear(lib, line):
            if it.id not in units:
                order.append(it)
                units[it.id] = 0
            units[it.id] += n
    return [(it, units[it.id]) for it in order]


def rows(lib, r: Rental) -> list[CheckRow]:
    """The rental's check rows, one per piece, in order: kept ticks and notes, new pieces added. Rows for
    pieces no longer on it go, unless they hold a note or photos."""
    have = {c.item_id: c for c in r.checks}
    out = [have.get(it.id) or CheckRow(it.id) for it, _n in pieces(lib, r)]
    on = {c.item_id for c in out}
    out += [c for c in r.checks if c.item_id not in on and (c.note.strip() or c.photos)]
    return out


def progress(checks: list[CheckRow], back: bool) -> tuple[int, int]:
    """(ticked, all) for checking out, or back in."""
    return sum(1 for c in checks if (c.back if back else c.out)), len(checks)
