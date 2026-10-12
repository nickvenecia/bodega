"""What gear has earned (core/earnings.py)."""

from __future__ import annotations

from decimal import Decimal

from bodega.core import earnings, pricing, sample
from bodega.core.model import RentalLine
from bodega.core.store import Library


def test_earned_on_rentals_that_went_out(tmp_path):
    lib = sample.fill(Library(tmp_path).load())
    r = next(iter(lib.rentals.values()))
    r.status = "booked"
    coming = earnings.earnings(lib)
    assert coming and all(e.amount == 0 for e in coming.values())
    assert sum(e.coming for e in coming.values()) > 0
    r.status = "returned"
    got = earnings.earnings(lib)
    b = lib.businesses.get(r.business_id) or lib.pricing()
    t = pricing.totals(lib, r, b)
    shared = sum(e.amount for e in got.values())
    assert abs(shared - (t.gear - t.discount * (t.gear / t.subtotal if t.subtotal else 0))) <= Decimal("0.05")
    assert all(r.id in e.rentals for e in got.values())


def test_paid_off(tmp_path):
    lib = sample.fill(Library(tmp_path).load())
    it = next(i for i in lib.items.values() if i.value)
    it.qty = 2
    paid = earnings.paid_for(it)
    assert earnings.paid_off(it, paid) == 1
    it.value = ""
    assert earnings.paid_off(it, Decimal(10)) is None


def test_fees_and_cancelled_dont_count(tmp_path):
    lib = sample.fill(Library(tmp_path).load())
    r = next(iter(lib.rentals.values()))
    r.lines = [RentalLine("fee", "", 1, "50", "Delivery")]
    r.status = "returned"
    assert earnings.earnings(lib) == {}
