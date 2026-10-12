"""Send to Cobro: a rental becomes a draft invoice in Cobro's data folder, in Cobro's format."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from bodega.core import money, pricing, sample
from bodega.core.store import Library
from bodega.services import cobro


@pytest.fixture
def cobro_home(tmp_path, monkeypatch):
    home = tmp_path / "Cobro"
    monkeypatch.setenv("COBRO_DATA_DIR", str(home))
    return home


def test_not_set_up(tmp_path, cobro_home):
    lib = sample.fill(Library(tmp_path / "b").load())
    assert not cobro.installed()
    with pytest.raises(OSError):
        cobro.send(lib, next(iter(lib.rentals.values())), lib.pricing())


def test_draft_invoice_matches_the_rental(tmp_path, cobro_home):
    lib = sample.fill(Library(tmp_path / "b").load())
    r = next(iter(lib.rentals.values()))
    r.discount, r.tax_rate = "10", "8.25"
    b = lib.businesses.get(r.business_id) or lib.pricing()
    cobro_home.mkdir(parents=True)
    me = {"id": "biz1", "name": b.name, "prefix": "JL", "number_style": "year", "terms_days": 30}
    (cobro_home / "businesses.json").write_text(json.dumps([{"id": "other", "name": "Someone"}, me]))
    (cobro_home / "invoices").mkdir()
    year = __import__("bodega.core.dates", fromlist=["today"]).today().year
    (cobro_home / "invoices" / "old.json").write_text(json.dumps({"number": f"JL-{year}-007"}))
    number = cobro.send(lib, r, b)
    assert number == f"JL-{year}-008"
    inv = next(
        json.loads(f.read_text()) for f in (cobro_home / "invoices").glob("*.json") if f.name != "old.json"
    )
    assert inv["business_id"] == "biz1" and inv["status"] == "draft" and inv["terms_days"] == 30
    assert inv["client"]["name"] == (r.client.company or r.client.name)
    # Cobro's math (qty × rate, minus the discount amount, plus tax %) gives the rental's total
    sub = sum((money.parse(i["qty"]) * money.parse(i["rate"]) for i in inv["items"]), Decimal(0))
    taxable = sub - money.parse(inv["discount"])
    total = money.cents(taxable + money.cents(taxable * money.parse(inv["tax_rate"]) / 100))
    assert total == pricing.totals(lib, r, b).total
    assert not (cobro_home / "businesses.json").with_suffix(".json.unreadable").exists()
