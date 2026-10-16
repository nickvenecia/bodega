"""Pricing (core/pricing.py): day rates, attached gear, packages, billed days, line dates, availability."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from bodega.core import pricing, sample
from bodega.core.model import Business, Item, Package, PackageLine, Rental, RentalLine
from bodega.core.store import Library


@pytest.fixture
def lib(data_folder):
    return sample.fill(Library(data_folder).load())


def b() -> Business:
    return Business(name="Test", rate_pct="4", value_tax="8.25", week_days=3)


def named(lib, text: str) -> Item:
    return next(i for i in lib.items.values() if text in i.name)


def test_replacement_and_auto_rate():
    it = Item(value="5998")
    assert pricing.replacement(it, b()) == Decimal("6492.84")  # paid + 8.25% tax
    assert pricing.auto_day_rate(it, b()) == Decimal(260)  # 4%, whole dollars
    it.day_rate = "250"
    assert pricing.own_rate(it, b()) == Decimal(250)
    it.rentable = False
    assert pricing.own_rate(it, b()) == 0


@pytest.mark.parametrize(
    ("days", "week", "billed"),
    [
        (1, 3, 1),
        (2, 3, 2),
        (3, 3, 3),
        (5, 3, 3),
        (7, 3, 3),
        (8, 3, 4),
        (10, 3, 6),
        (14, 3, 6),
        (5, 4, 4),
        (6, 7, 6),
    ],
)
def test_billed_days(days, week, billed):
    assert pricing.billed_for(days, week) == billed


def test_weekend_deal():
    fri = date(2026, 10, 9)
    r = Rental(pickup=fri.isoformat(), return_date=(fri + timedelta(days=3)).isoformat())
    assert pricing.rental_days(r, b()).billed == 1
    r.weekend_deal = False
    assert pricing.rental_days(r, b()).billed == 3
    r.billed_days = "2"
    assert pricing.rental_days(r, b()).billed == 2


def test_attached_gear_rides_along_and_is_shared_out(lib):
    fx6 = named(lib, "Sony FX6")
    gear = pricing.with_attached(lib, fx6, 1)
    assert len(gear) == 4  # body + cage + handle + cable
    light = named(lib, "STORM 80c LED")
    one = {it.name: u for it, u, _d in pricing.with_attached(lib, light, 1)}
    assert one["CF4 Fresnel for STORM 80c"] == 1  # 2 fresnels across 3 lights, rounded up
    three = {it.name: u for it, u, _d in pricing.with_attached(lib, light, 3)}
    assert three["CF4 Fresnel for STORM 80c"] == 2
    assert pricing.item_rate(lib, fx6, b()) > pricing.own_rate(fx6, b())


def test_package_discount(lib):
    pkg = next(iter(lib.packages.values()))
    alone = pricing.package_sum(lib, pkg, b())
    pkg.pricing, pkg.discount = "discount", "20"
    assert pricing.package_rate(lib, pkg, b()) == (alone * Decimal("0.8")).quantize(Decimal(1))
    pkg.pricing, pkg.day_rate = "fixed", "300"
    assert pricing.package_rate(lib, pkg, b()) == 300
    pkg.pricing = "sum"
    assert pricing.package_rate(lib, pkg, b()) == alone


def test_lines_with_their_own_dates(lib):
    """The FX6 package Sunday to Sunday, the lights Monday to Wednesday, on one rental."""
    r = next(iter(lib.rentals.values()))
    t = pricing.totals(lib, r, b())
    assert t.mixed
    assert [d.billed for d in t.line_days[:3]] == [3, 2, 2]
    assert len(pricing.periods(r)) == 2
    pick, ret = pricing.span_of(r)
    assert (ret - pick).days == 7
    # the gear total is every line's own days, plus the flat fee
    assert t.total == sum(t.line_amounts, Decimal(0))


def test_double_booking_respects_line_dates(lib):
    r = next(iter(lib.rentals.values()))
    light = named(lib, "STORM 80c LED")
    other = Rental(number="X-1", status="booked", business_id=r.business_id)
    # the lights are free again Wednesday, so a Wednesday-to-Friday booking of all 3 fits…
    wed = date.fromisoformat(r.lines[1].return_date)
    other.pickup, other.return_date = wed.isoformat(), (wed + timedelta(days=2)).isoformat()
    other.lines = [RentalLine("item", light.id, 3)]
    lib.rentals[other.id] = other
    assert pricing.shortages(lib, other) == []
    # …but Tuesday clashes: 2 are out on the first rental, only 1 is free
    other.pickup = (wed - timedelta(days=1)).isoformat()
    short = pricing.shortages(lib, other)
    assert short and short[0].item.id == light.id and short[0].free == 1
    assert "JLF-" in short[0].why


def test_repair_is_never_free(lib):
    r = next(iter(lib.rentals.values()))
    named(lib, "Shotgun").status = "repair"
    r.lines.append(RentalLine("item", named(lib, "Shotgun").id))
    assert any(s.why == "In repair" for s in pricing.shortages(lib, r))


def test_out_now(lib):
    r = next(iter(lib.rentals.values()))
    r.status = "out"
    r.pickup = date.today().isoformat()
    r.lines[1].pickup = (date.today() + timedelta(days=5)).isoformat()
    out = pricing.out_now(lib)
    assert named(lib, "Sony FX6").id in out
    assert named(lib, "STORM 80c LED").id not in out  # its own dates haven't started


def test_package_of_unknown_gear_is_harmless(lib):
    p = Package(lines=[PackageLine("nope", 2)])
    assert pricing.package_sum(lib, p, b()) == 0


def test_a_booked_rentals_prices_hold_when_rates_change(lib, data_folder):
    """Industry practice: a quote follows today's rates; once booked, the price is what was agreed."""
    r = next(iter(lib.rentals.values()))
    prof = lib.businesses[r.business_id]
    r.status = "quote"
    lib.save_rental(r)
    piece = next(lib.items[ln.ref] for ln in r.lines if ln.kind == "item" and not ln.rate)
    quoted = pricing.totals(lib, r, prof).total
    piece.day_rate = "999"
    assert pricing.totals(lib, r, prof).total != quoted  # a quote follows
    piece.day_rate = ""
    r.status = "booked"
    lib.save_rental(r)
    booked = pricing.totals(lib, r, prof).total
    assert booked == quoted
    piece.day_rate, piece.name = "999", "Renamed"
    prof.rate_pct, prof.week_days = "9", 7
    lib.save_items()
    lib.save_businesses()
    again = Library(data_folder).load()
    r2 = again.rentals[r.id]
    assert pricing.totals(again, r2, again.businesses[r2.business_id]).total == booked
    line = next(ln for ln in r2.lines if ln.ref == piece.id)
    assert pricing.line_name(again, line) != "Renamed"  # the name it was booked under
    for status in ("out", "returned"):
        r2.status = status
        again.save_rental(r2)
        assert pricing.totals(again, r2, again.businesses[r2.business_id]).total == booked
    r2.status = "quote"  # back to a quote: today's prices again
    again.save_rental(r2)
    assert pricing.totals(again, r2, again.businesses[r2.business_id]).total != booked


def test_a_booked_lines_quantity_keeps_its_price_for_each(lib):
    r = next(iter(lib.rentals.values()))
    prof = lib.businesses[r.business_id]
    line = next(ln for ln in r.lines if ln.kind == "item" and not ln.rate)
    line.qty = 1
    r.status = "booked"
    lib.save_rental(r)
    one = pricing.line_day(lib, line, prof)
    lib.items[line.ref].day_rate = "5000"
    line.qty = 3
    assert pricing.line_day(lib, line, prof) == one * 3


def test_rentals_booked_before_this_lock_when_read(data_folder):
    lib = sample.fill(Library(data_folder).load())
    r = next(iter(lib.rentals.values()))
    r.status = "booked"
    lib.save_rental(r)
    for ln in r.lines:  # as an older Bodega wrote it
        ln.locked_day, ln.locked_qty = "", 0
    r.week_days = 0
    from bodega.core.store import write_json

    write_json(data_folder / "rentals" / f"{r.id}.json", r.to_dict())
    again = Library(data_folder).load()
    assert all(ln.locked_day for ln in again.rentals[r.id].lines if ln.kind != "fee" and not ln.rate)
    assert again.rentals[r.id].week_days == again.businesses[r.business_id].week_days


def test_a_suggested_deposit_is_the_profiles_percent_or_ten(lib):
    from bodega.core import money

    r = next(iter(lib.rentals.values()))
    plain = b()
    value = pricing.totals(lib, r, plain).value
    assert pricing.suggested_deposit(lib, r, plain) == money.whole(value * Decimal("0.10"))
    plain.deposit_pct = "20"
    assert pricing.suggested_deposit(lib, r, plain) == money.whole(value * Decimal("0.20"))
    assert pricing.deposit_pct(None) == pricing.DEFAULT_DEPOSIT_PCT
