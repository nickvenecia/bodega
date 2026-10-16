"""What each piece of gear has earned: its share of every rental that went out (Out or Returned).

A rental line's amount (after the rental's discount, before tax; fees aren't gear) is shared among the gear it
sent out by each piece's own day rate: a kit's price is split across what's in it, and a camera line's price
across the camera and what's attached. Booked rentals count as "coming", not earned.

"Paid for itself" compares what it earned with what you paid for all of them (Paid Each × How Many).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from bodega.core import money, pricing
from bodega.core.money import ZERO

EARNED = ("out", "returned")
COMING = ("booked",)


@dataclass
class Earned:
    amount: Decimal = ZERO  # from rentals that went out
    coming: Decimal = ZERO  # from booked rentals
    rentals: set[str] = field(default_factory=set)  # the rentals it earned on
    days: int = 0  # billed days out


def _shares(lib, line, b) -> list[tuple[str, Decimal]]:
    """(item id, weight) for the gear a line sends out: its own day rate × units (equal shares if all free)."""
    gear = pricing.line_gear(lib, line)
    weights = [(it.id, pricing.own_rate(it, b) * units) for it, units, _d in gear]
    total = sum((w for _i, w in weights), ZERO)
    if total <= 0:
        n = len(weights)
        return [(i, Decimal(1) / n) for i, _w in weights] if n else []
    return [(i, w / total) for i, w in weights]


@pricing.one_pass
def earnings(lib) -> dict[str, Earned]:
    out: dict[str, Earned] = {}
    for r in lib.rentals.values():
        if r.status not in EARNED + COMING:
            continue
        b = lib.businesses.get(r.business_id) or lib.pricing()
        t = pricing.totals(lib, r, b)
        keep = Decimal(1) - (t.discount / t.subtotal if t.subtotal else ZERO)  # the rental's discount, shared
        for line, amount, days in zip(r.lines, t.line_amounts, t.line_days, strict=False):
            if line.kind == "fee" or amount <= 0:
                continue
            for item_id, share in _shares(lib, line, b):
                e = out.setdefault(item_id, Earned())
                part = amount * keep * share
                if r.status in EARNED:
                    e.amount += part
                    e.rentals.add(r.id)
                    e.days += days.billed
                else:
                    e.coming += part
    for e in out.values():
        e.amount = money.cents(e.amount)
        e.coming = money.cents(e.coming)
    return out


def paid_for(item) -> Decimal:
    """What you paid for all of them."""
    return max(ZERO, money.parse(item.value)) * item.qty


def paid_off(item, earned: Decimal) -> Decimal | None:
    """How much of what it cost it has earned back (1 = paid for itself), or None if you didn't say what it cost."""
    paid = paid_for(item)
    return earned / paid if paid > 0 else None
