"""The figure row above each list (the standard's 4.3): three or four figures about the whole list, the same on every
visit, whatever the search or filters hide. A figure that's a slice of the list (`slice`: the gear filter or the
place it turns on) filters it when pressed; a sum is plain. A tone colours the number only, and follows good or bad,
never importance: a zero is never red. No Qt here.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from bodega.core import earnings, money, pricing

TONES = ("", "good", "warn", "bad")


@dataclass(frozen=True)
class Figure:
    key: str
    label: str
    value: str
    tone: str = ""
    slice: str = ""  # what pressing it turns on: a gear filter ("out", "repair") or a place ("out", "upcoming")
    tip: str = ""  # more about it, on hover


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


EARNED_TIP = "An estimate: each rental's gear total, shared out by each piece's day rate"


def piece(lib, it, b, earned: earnings.Earned | None) -> list[Figure]:
    """A piece's strip, under its head: its day rate (all of them, with what goes with it), what it has earned (or,
    before it has, what's booked), and how much of what it cost that is."""
    cur = (b.currency if b else "$") or "$"
    out = []
    rate = pricing.item_rate(lib, it, b, it.qty)
    if it.rentable and rate:
        kids = len(pricing.with_attached(lib, it, 1)) > 1
        tip = " and ".join(x for x in (f"all {it.qty}" if it.qty > 1 else "", "what goes with it" if kids else "") if x)
        out.append(Figure("rate", "Day Rate", money.fmt_short(rate, cur), tip=f"For {tip}" if tip else ""))
    made = earned.amount if earned is not None else money.ZERO
    coming = earned.coming if earned is not None else money.ZERO
    n = len(earned.rentals) if earned is not None else 0
    rentals = f"{n} Rental{'s' if n != 1 else ''}"
    booked = f"Plus {money.fmt_short(money.whole(coming), cur)} booked. " if coming else ""
    if made:
        out.append(
            Figure("earned", f"Earned, {rentals}", money.fmt_short(money.whole(made), cur), tip=booked + EARNED_TIP)
        )
    elif coming:
        out.append(Figure("earned", "Booked", money.fmt_short(money.whole(coming), cur), tip=EARNED_TIP))
    share = earnings.paid_off(it, made) if made else None
    if share is not None:
        if share >= 1:
            out.append(
                Figure("payoff", "Paid for Itself", f"{share:.1f}×", "good", tip="What it has earned, by what it cost")
            )
        else:
            out.append(Figure("payoff", "Paid Off", f"{share * 100:.0f}%", tip="What it has earned, of what it cost"))
    return out


def kit(lib, p, b) -> list[Figure]:
    """A kit's strip, under its name: its day rate, a week of it, and the pieces in it."""
    cur = (b.currency if b else "$") or "$"
    wd = b.week_days if b else 7
    rate = pricing.package_rate(lib, p, b)
    pieces = sum(u for _i, u, _d in pricing.package_gear(lib, p))
    return [
        Figure("rate", "Day Rate", money.fmt_short(rate, cur)),
        Figure("week", "Week", money.fmt_short(rate * wd, cur), tip=f"A week is {wd} billed days (your profile)"),
        Figure("pieces", "Pieces", f"{pieces:,}"),
    ]


def rental(lib, r, t: pricing.Totals, b) -> list[Figure]:
    """A rental's strip, under its head: what it comes to, the days billed (or, with lines on their own dates, the
    periods), and the pieces going out."""
    cur = (b.currency if b else "$") or "$"
    pieces = sum(u for line in r.lines for _it, u, _d in pricing.line_gear(lib, line))
    days = (
        Figure("days", "Periods", f"{len(pricing.periods(r)):,}", tip="Lines with dates of their own")
        if t.mixed
        else Figure("days", "Billed Days", f"{t.days.billed:,}")
    )
    total = Figure("total", "Total", money.fmt_short(t.total, cur), tip=money.fmt(t.total, cur))  # (cents on hover)
    out = [total, days, Figure("pieces", "Pieces", f"{pieces:,}")]
    if t.deposit:
        out.append(Figure("deposit", "Deposit", money.fmt_short(t.deposit, cur), tip="Refundable"))
    return out
