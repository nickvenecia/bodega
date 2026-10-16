"""How Bodega prices gear, packages and rentals, and keeps gear from being promised twice.

The rules, in plain words:

- **Replacement value** of one unit = what you paid × (1 + your sales tax). That's what a renter owes if
  it's lost, and the number insurance asks for.
- **Day rate** of one unit = a percent of its replacement value (4% by default), rounded to whole dollars.
  Type your own day rate on any item to override it.
- Gear that's **attached** to another item (a cage that lives on the FX6) goes with it: the FX6's line on a
  rental costs the FX6 plus everything attached to it.
- A **package** costs what its gear adds up to, less a discount (15% by default), or a day rate you set.
- A **rental** is billed in days, and every line can have dates of its own (the FX6 package Sunday to
  Sunday, the FX3 package Monday to Wednesday, on the same production). Each line is billed in days: nights between pickup and return (at least one). A 7-day week is billed
  as `week_days` days (3 by default, the usual rental-house week), so 5 days out costs 3 days and
  10 days out costs 3 + 3 = 6. Pick up Friday and return Monday counts as one day (the weekend deal).
- Total = gear per day × billed days + fees, less the discount, plus sales tax on the rental.
  The security deposit is listed separately: it's refundable and not part of the price.
- **A rental's prices lock when it's booked** (as rental houses do): a quote follows today's day rates, kit
  prices and the profile's pricing; once a rental is booked (and while it's out, returned or cancelled) each line
  keeps what it cost a day, and its name, and the rental keeps the profile's week. Back to a quote, it follows
  again. `settle()` does it whenever a rental is saved.

No Qt in here: everything takes the Library (or anything with .items / .packages / .rentals dicts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from bodega.core import dates, money
from bodega.core.model import Business, Item, Package, Rental, RentalLine

ZERO = money.ZERO


# ---------------------------------------------------------------------------- items
def replacement(item: Item, b: Business | None) -> Decimal:
    """Replacement value of one unit, with sales tax."""
    tax = money.pct(b.value_tax) if b else ZERO
    return money.cents(max(ZERO, money.parse(item.value)) * (1 + tax))


def auto_day_rate(item: Item, b: Business | None) -> Decimal:
    rate = money.pct(b.rate_pct) if b else ZERO
    return money.whole(replacement(item, b) * rate)


def own_rate(item: Item, b: Business | None) -> Decimal:
    """One unit's day rate on its own (your typed rate, or the automatic one). Not-rentable gear is 0."""
    if not item.rentable:
        return ZERO
    if item.day_rate.strip():
        return money.cents(max(ZERO, money.parse(item.day_rate)))
    return auto_day_rate(item, b)


def children(lib, item_id: str) -> list[Item]:
    """What's attached to this item, in name order."""
    kids = [i for i in lib.items.values() if i.parent == item_id and i.id != item_id]
    return sorted(kids, key=lambda i: i.name.casefold())


def root_of(lib, item: Item) -> Item:
    """The item this one ultimately lives with (itself if it's not attached to anything)."""
    seen = {item.id}
    cur = item
    while cur.parent and cur.parent in lib.items and cur.parent not in seen:
        seen.add(cur.parent)
        cur = lib.items[cur.parent]
    return cur


def with_attached(lib, item: Item, qty: int = 1) -> list[tuple[Item, int, int]]:
    """The item and everything attached to it (and attached to those): (item, units, depth).

    Attached gear is shared out across the parent's units, rounded up: with 3 lights and 2 fresnels
    attached, one light goes out with 1 fresnel and all 3 go out with both."""
    out: list[tuple[Item, int, int]] = []
    seen: set[str] = set()

    def walk(it: Item, units: int, depth: int) -> None:
        if it.id in seen:
            return
        seen.add(it.id)
        out.append((it, units, depth))
        for kid in children(lib, it.id):
            walk(kid, -(-kid.qty * units // max(1, it.qty)), depth + 1)

    walk(item, qty, 0)
    return out


def item_rate(lib, item: Item, b: Business | None, qty: int = 1) -> Decimal:
    """Day rate for `qty` of this item WITH the gear attached to it (what its line on a rental costs a day)."""
    return sum((own_rate(it, b) * units for it, units, _d in with_attached(lib, item, qty)), ZERO)


def item_value(lib, item: Item, b: Business | None, qty: int = 1) -> Decimal:
    return sum((replacement(it, b) * units for it, units, _d in with_attached(lib, item, qty)), ZERO)


@dataclass
class Stock:
    """What some gear adds up to, the way a gear sheet totals it."""

    pieces: int = 0
    paid: Decimal = ZERO  # what it all cost, before tax
    value: Decimal = ZERO  # with tax: replacement value
    day: Decimal = ZERO  # every piece's own day rate, for all units

    @property
    def tax(self) -> Decimal:
        return self.value - self.paid

    def add(self, other: Stock) -> None:
        self.pieces += other.pieces
        self.paid += other.paid
        self.value += other.value
        self.day += other.day


def stock(lib, item: Item, b: Business | None, attached: bool = True) -> Stock:
    """All units of this item, and (with `attached`) everything attached to it, totalled."""
    out = Stock()
    gear = with_attached(lib, item, item.qty) if attached else [(item, item.qty, 0)]
    for it, units, _d in gear:
        if it.status == "retired":
            continue
        out.pieces += units
        out.paid += money.cents(max(ZERO, money.parse(it.value)) * units)
        out.value += replacement(it, b) * units
        out.day += own_rate(it, b) * units
    return out


# ---------------------------------------------------------------------------- packages
def package_gear(lib, pkg: Package) -> list[tuple[Item, int, int]]:
    """Every piece of gear in a package, attached gear included: (item, units, depth)."""
    out: list[tuple[Item, int, int]] = []
    for line in pkg.lines:
        it = lib.items.get(line.item_id)
        if it is not None:
            out.extend(with_attached(lib, it, line.qty))
    return out


def package_sum(lib, pkg: Package, b: Business | None) -> Decimal:
    """What the package's gear adds up to per day, rented piece by piece."""
    return sum((own_rate(it, b) * units for it, units, _d in package_gear(lib, pkg)), ZERO)


def package_rate(lib, pkg: Package, b: Business | None) -> Decimal:
    gear = package_sum(lib, pkg, b)
    if pkg.pricing == "fixed" and pkg.day_rate.strip():
        return money.cents(max(ZERO, money.parse(pkg.day_rate)))
    if pkg.pricing == "discount":
        off = min(Decimal(1), money.pct(pkg.discount))
        return money.whole(gear * (1 - off))
    return gear


def package_value(lib, pkg: Package, b: Business | None) -> Decimal:
    return sum((replacement(it, b) * units for it, units, _d in package_gear(lib, pkg)), ZERO)


# ---------------------------------------------------------------------------- days
def nights(pickup: date | None, ret: date | None) -> int:
    if pickup is None or ret is None:
        return 1
    return max(1, (ret - pickup).days)


def is_weekend(pickup: date | None, ret: date | None) -> bool:
    """Friday pickup, Monday return."""
    return pickup is not None and ret is not None and pickup.weekday() == 4 and (ret - pickup).days == 3


def billed_for(n: int, week_days: int) -> int:
    """Days billed for n days out, with a 7-day week billed as week_days."""
    weeks, rest = divmod(max(1, n), 7)
    return weeks * week_days + min(rest, week_days)


@dataclass(frozen=True)
class Days:
    out: int  # days (nights) the gear is out
    billed: int
    why: str  # "5 days out, billed as 3 (3-day week)"
    manual: bool = False


def week_days(r: Rental | None, b: Business | None) -> int:
    """How many days a 7-day week of this rental is billed as: kept on it once booked, else the profile's."""
    if r is not None and r.week_days:
        return r.week_days
    return b.week_days if b else 7


def days_for(
    pick: date | None, ret: date | None, b: Business | None, weekend_deal: bool, wd: int | None = None
) -> Days:
    n = nights(pick, ret)
    wd = wd or (b.week_days if b else 7)
    if weekend_deal and is_weekend(pick, ret):
        return Days(n, 1, "Friday to Monday, billed as 1 day (weekend)")
    billed = billed_for(n, wd)
    if billed == n:
        return Days(n, billed, f"{_days(n)}")
    return Days(n, billed, f"{_days(n)} out, billed as {billed} ({wd}-day week)")


def rental_days(r: Rental, b: Business | None) -> Days:
    """Days for the rental's own dates (lines without dates of their own)."""
    pick, ret = dates.parse(r.pickup), dates.parse(r.return_date)
    if r.billed_days.strip():
        n = nights(pick, ret)
        typed = money.parse(r.billed_days)
        days = max(1, int(typed)) if typed > 0 else 1
        return Days(n, days, f"{_days(n)} out, billed as {days} (typed)", True)
    return days_for(pick, ret, b, r.weekend_deal, week_days(r, b))


def line_dates(r: Rental, line: RentalLine) -> tuple[date | None, date | None]:
    """The dates a line's gear is out: its own if it has them, else the rental's."""
    if r.own_dates(line):
        a = dates.parse(line.pickup)
        z = dates.parse(line.return_date) or a
        return a, z
    return dates.parse(r.pickup), dates.parse(r.return_date)


def line_days(r: Rental, line: RentalLine, b: Business | None) -> Days:
    if r.own_dates(line):
        a, z = line_dates(r, line)
        return days_for(a, z, b, r.weekend_deal, week_days(r, b))
    return rental_days(r, b)


def span_of(r: Rental) -> tuple[date | None, date | None]:
    """First pickup to last return, across every line."""
    starts, ends = [], []
    for ln in [None, *r.lines]:
        a, z = (dates.parse(r.pickup), dates.parse(r.return_date)) if ln is None else line_dates(r, ln)
        if a:
            starts.append(a)
        if z or a:
            ends.append(z or a)
    return (min(starts) if starts else None, max(ends) if ends else None)


def periods(r: Rental) -> list[tuple[date | None, date | None]]:
    """The different date ranges on this rental, in order (one, unless lines have their own dates)."""
    seen: list[tuple[date | None, date | None]] = []
    for ln in r.lines:
        if ln.kind == "fee":
            continue
        w = line_dates(r, ln)
        if w not in seen:
            seen.append(w)
    if not seen:
        seen.append((dates.parse(r.pickup), dates.parse(r.return_date)))
    return sorted(seen, key=lambda w: (w[0] or date.min, w[1] or date.min))


def _days(n: int) -> str:
    return f"{n} day" if n == 1 else f"{n} days"


# ---------------------------------------------------------------------------- rentals
LOCKED = ("booked", "out", "returned", "cancelled")  # a rental's prices hold from booking on


def line_day(lib, line: RentalLine, b: Business | None) -> Decimal:
    """What this whole line costs per day, its quantity included (a fee: its flat amount × qty)."""
    if line.rate.strip():
        return money.cents(max(ZERO, money.parse(line.rate)) * line.qty)
    if line.locked_day and line.kind != "fee":
        held = max(ZERO, money.parse(line.locked_day))
        if line.qty == line.locked_qty:
            return money.cents(held)
        return money.cents(held / max(1, line.locked_qty) * line.qty)  # booked at that price for each
    return live_day(lib, line, b)


def live_day(lib, line: RentalLine, b: Business | None) -> Decimal:
    """What the line costs a day at today's rates (its gear's or kit's own)."""
    if line.kind == "item":
        it = lib.items.get(line.ref)
        return item_rate(lib, it, b, line.qty) if it else ZERO
    if line.kind == "package":
        pkg = lib.packages.get(line.ref)
        return package_rate(lib, pkg, b) * line.qty if pkg else ZERO
    return ZERO


def line_unit(lib, line: RentalLine, b: Business | None) -> Decimal:
    """The rate for one of this line, as shown in the Rate column."""
    if line.rate.strip():
        return money.cents(max(ZERO, money.parse(line.rate)))
    return money.cents(line_day(lib, line, b) / max(1, line.qty))


def line_gear(lib, line: RentalLine) -> list[tuple[Item, int, int]]:
    """The gear a rental line sends out: (item, units, depth). Depth 0 is the line's own item, or a
    package's own lines; deeper is attached gear."""
    if line.kind == "item":
        it = lib.items.get(line.ref)
        return with_attached(lib, it, line.qty) if it else []
    if line.kind == "package":
        pkg = lib.packages.get(line.ref)
        if pkg is None:
            return []
        out = []
        for pl in pkg.lines:
            it = lib.items.get(pl.item_id)
            if it is not None:
                out.extend(with_attached(lib, it, pl.qty * line.qty))
        return out
    return []


def settle(lib, r: Rental, b: Business | None) -> bool:
    """Lock a booked rental's prices, or let a quote follow today's again. True if anything changed."""
    changed = False
    if r.status in LOCKED:
        for line in r.lines:
            if line.kind == "fee" or line.rate.strip() or line.locked_day:
                continue
            line.locked_day, line.locked_qty = str(live_day(lib, line, b)), line.qty
            line.name = line_name(lib, line)
            changed = True
        if not r.week_days and b is not None:
            r.week_days = b.week_days
            changed = True
    else:
        for line in r.lines:
            if line.locked_day:
                line.locked_day, line.locked_qty = "", 0
                changed = True
        if r.week_days:
            r.week_days = 0
            changed = True
    return changed


def line_name(lib, line: RentalLine) -> str:
    if line.locked_day and line.name:  # booked under this name
        return line.name
    if line.kind == "item":
        it = lib.items.get(line.ref)
        return it.name if it else (line.name or "Removed gear")
    if line.kind == "package":
        pkg = lib.packages.get(line.ref)
        return pkg.name if pkg else (line.name or "Removed package")
    return line.name


@dataclass(frozen=True)
class Totals:
    per_day: Decimal  # all gear, one day
    days: Days  # the rental's own dates
    gear: Decimal  # every gear line × its billed days
    fees: Decimal
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    deposit: Decimal
    value: Decimal  # replacement value of everything going out
    line_amounts: list[Decimal] = field(default_factory=list)  # each line's amount for the whole rental
    line_days: list[Days] = field(default_factory=list)
    mixed: bool = False  # lines with different dates


def totals(lib, r: Rental, b: Business | None) -> Totals:
    days = rental_days(r, b)
    per_day = fees = value = gear = ZERO
    amounts: list[Decimal] = []
    each_days: list[Days] = []
    for line in r.lines:
        day = line_day(lib, line, b)
        ld = line_days(r, line, b)
        each_days.append(ld)
        if line.kind == "fee":
            amt = money.cents(day)
            fees += amt
        else:
            per_day += day
            amt = money.cents(day * ld.billed)
            gear += amt
            value += sum((replacement(it, b) * units for it, units, _d in line_gear(lib, line)), ZERO)
        amounts.append(amt)
    subtotal = gear + fees
    discount = money.cents(subtotal * min(Decimal(1), money.pct(r.discount)))
    taxable = max(ZERO, subtotal - discount)
    tax = money.cents(taxable * money.pct(r.tax_rate))
    deposit = money.cents(max(ZERO, money.parse(r.deposit)))
    mixed = len(periods(r)) > 1
    return Totals(
        per_day,
        days,
        gear,
        fees,
        subtotal,
        discount,
        tax,
        taxable + tax,
        deposit,
        value,
        amounts,
        each_days,
        mixed,
    )


def suggested_deposit(lib, r: Rental, b: Business | None) -> Decimal:
    if b is None or not b.deposit_pct.strip():
        return ZERO
    t = totals(lib, r, b)
    return money.whole(t.value * money.pct(b.deposit_pct))


# ---------------------------------------------------------------------------- availability
def _window(a: date | None, z: date | None) -> tuple[date, date] | None:
    """Gear returned on a day can go out again that day; a same-day rental holds its day."""
    if a is None:
        return None
    z = z or a
    return a, max(z, dates.plus(a, 1))


@dataclass(frozen=True)
class Booking:
    item_id: str
    units: int
    start: date
    end: date  # the day it's free again
    rental: Rental


def bookings(lib, r: Rental) -> list[Booking]:
    """Every piece of gear this rental sends out, with the dates its line has it."""
    out = []
    for line in r.lines:
        w = _window(*line_dates(r, line))
        if w is None:
            continue
        for it, units, _d in line_gear(lib, line):
            out.append(Booking(it.id, units, w[0], w[1], r))
    return out


def units_needed(lib, r: Rental) -> dict[str, int]:
    need: dict[str, int] = {}
    for line in r.lines:
        for it, units, _d in line_gear(lib, line):
            need[it.id] = need.get(it.id, 0) + units
    return need


@dataclass(frozen=True)
class Short:
    item: Item
    needed: int
    free: int
    why: str  # "Also on DP-2026-004" / "In repair"


def shortages(lib, r: Rental) -> list[Short]:
    """Gear this rental needs that isn't free on its dates (in repair, retired, or promised elsewhere).
    Each line counts on its own dates, so two lines on different days don't clash."""
    if r.status in ("returned", "cancelled"):
        return []
    mine = bookings(lib, r)
    others = [bk for o in lib.rentals.values() if o.id != r.id and o.holds_gear() for bk in bookings(lib, o)]
    by_item: dict[str, list[Booking]] = {}
    for bk in mine:
        by_item.setdefault(bk.item_id, []).append(bk)
    out = []
    for item_id, own in by_item.items():
        it = lib.items.get(item_id)
        if it is None:
            continue
        if it.status != "ready":
            out.append(
                Short(it, max(bk.units for bk in own), 0, "In repair" if it.status == "repair" else "Retired")
            )
            continue
        theirs = [bk for bk in others if bk.item_id == item_id]
        worst_need, worst_free, where = 0, it.qty, set()
        # check the busiest moment: every day one of these bookings starts
        for day in sorted({bk.start for bk in own + theirs}):
            need = sum(bk.units for bk in own if bk.start <= day < bk.end)
            if not need:
                continue
            busy = [bk for bk in theirs if bk.start <= day < bk.end]
            free = max(0, it.qty - sum(bk.units for bk in busy))
            if need > free and (need - free) > (worst_need - worst_free):
                worst_need, worst_free = need, free
                where = {bk.rental.number for bk in busy}
        if worst_need:
            why = "Also on " + ", ".join(sorted(where)) if where else f"You have {it.qty}"
            out.append(Short(it, worst_need, worst_free, why))
    return sorted(out, key=lambda s: s.item.name.casefold())


@dataclass(frozen=True)
class Day:
    day: date
    booked: int  # units held by booked or out rentals
    free: int
    rentals: tuple[Rental, ...]


def schedule(lib, item: Item, start: date, days: int) -> list[Day]:
    """Day by day, how many of this item are held and by which rentals (for the overview's calendar)."""
    mine = [
        bk for r in lib.rentals.values() if r.holds_gear() for bk in bookings(lib, r) if bk.item_id == item.id
    ]
    out = []
    for n in range(days):
        d = dates.plus(start, n)
        here = [bk for bk in mine if bk.start <= d < bk.end]
        booked = sum(bk.units for bk in here)
        free = 0 if item.status != "ready" else max(0, item.qty - booked)
        seen: list[Rental] = []
        for bk in here:
            if bk.rental not in seen:
                seen.append(bk.rental)
        out.append(Day(d, booked, free, tuple(seen)))
    return out


def rentals_with(
    lib, item: Item, upcoming_only: bool = True
) -> list[tuple[Rental, int, date | None, date | None]]:
    """Rentals this item is on (as itself or attached to something): (rental, units, first day, last day).
    Upcoming only skips returned, cancelled and anything that ended before today."""
    today = dates.today()
    out = []
    for r in lib.rentals.values():
        if upcoming_only and r.status in ("returned", "cancelled"):
            continue
        units, first, last = 0, None, None
        for line in r.lines:
            n = sum(u for it, u, _d in line_gear(lib, line) if it.id == item.id)
            if not n:
                continue
            units += n
            a, z = line_dates(r, line)
            first = a if first is None or (a and a < first) else first
            z = z or a
            last = z if last is None or (z and z > last) else last
        if units and not (upcoming_only and last is not None and last < today and r.status != "out"):
            out.append((r, units, first, last))
    return sorted(out, key=lambda x: (x[2] or today, x[0].number))


def units_out(lib) -> dict[str, int]:
    """How many of each item are out the door right now (on rentals marked Out, lines already started)."""
    today = dates.today()
    out: dict[str, int] = {}
    for r in lib.rentals.values():
        if r.status != "out":
            continue
        for line in r.lines:
            a, _z = line_dates(r, line)
            if a is not None and a > today:
                continue
            for it, units, _d in line_gear(lib, line):
                out[it.id] = out.get(it.id, 0) + units
    return out


def out_now(lib) -> dict[str, str]:
    """Gear that's out right now: item id -> the rental number it's out on. On a rental that's out, a line
    with later dates of its own isn't out yet, and one with earlier dates counts until the rental's back."""
    today = dates.today()
    out: dict[str, str] = {}
    for r in lib.rentals.values():
        if r.status != "out":
            continue
        for line in r.lines:
            a, _z = line_dates(r, line)
            if a is not None and a > today:
                continue
            for it, _u, _d in line_gear(lib, line):
                out.setdefault(it.id, r.number)
    return out


def late(r: Rental) -> bool:
    ret = span_of(r)[1]
    return r.status == "out" and ret is not None and ret < dates.today()
