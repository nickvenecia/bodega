"""The figure row above each list (the standard's 4.3): three or four figures about the whole list, the same on every
visit, whatever the search or filters hide. A figure that's a slice of the list (`slice`: the gear filter or the
place it turns on) filters it when pressed; a sum is plain. A tone colours the number only, and follows good or bad,
never importance: a zero is never red. No Qt here.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from bodega.core import money, pricing

TONES = ("", "warn", "bad")


@dataclass(frozen=True)
class Figure:
    key: str
    label: str
    value: str
    tone: str = ""
    slice: str = ""  # what pressing it turns on: a gear filter ("out", "repair") or a place ("out", "upcoming")


def gear(lib, group: str = "") -> list[Figure]:
    """Pieces (every unit), how many pieces are out and in repair, and what it would all cost to replace: of
    everything not retired, or of one group's."""
    items = [i for i in lib.items.values() if not i.is_retired() and (not group or i.group == group)]
    b = lib.pricing()
    cur = (b.currency if b else "$") or "$"
    with pricing.indexed(lib):
        out = pricing.units_out(lib)
        value = sum((pricing.replacement(i, b) * i.qty for i in items), Decimal(0))
    n_out = sum(1 for i in items if out.get(i.id, 0) > 0)
    n_repair = sum(1 for i in items if i.in_repair())
    return [
        Figure("pieces", "Pieces", f"{sum(i.qty for i in items):,}"),
        Figure("out", "Out", f"{n_out:,}", slice="out"),
        Figure("repair", "In Repair", f"{n_repair:,}", "warn" if n_repair else "", slice="repair"),
        Figure("value", "Replacement Value", money.fmt_short(money.whole(value), cur)),
    ]


def kits(lib) -> list[Figure]:
    """Kits, the pieces in them, and a day of every kit."""
    b = lib.pricing()
    cur = (b.currency if b else "$") or "$"
    with pricing.indexed(lib):
        pieces = sum(sum(u for _i, u, _d in pricing.package_gear(lib, p)) for p in lib.packages.values())
        rate = sum((pricing.package_rate(lib, p, b) for p in lib.packages.values()), Decimal(0))
    return [
        Figure("kits", "Kits", f"{len(lib.packages):,}"),
        Figure("pieces", "Pieces in Them", f"{pieces:,}"),
        Figure("rate", "A Day of Every Kit", money.fmt_short(rate, cur)),
    ]


def rentals(lib) -> list[Figure]:
    """Out now, coming up (the sidebar's places, so pressing one goes there), late, and quotes waiting."""
    rs = list(lib.rentals.values())
    late = sum(1 for r in rs if pricing.late(r))
    return [
        Figure("out", "Out Now", f"{sum(1 for r in rs if r.is_out()):,}", slice="out"),
        Figure("upcoming", "Coming Up", f"{sum(1 for r in rs if pricing.coming_up(r)):,}", slice="upcoming"),
        Figure("late", "Late", f"{late:,}", "bad" if late else ""),
        Figure("quotes", "Quotes", f"{sum(1 for r in rs if r.is_quote()):,}"),
    ]
