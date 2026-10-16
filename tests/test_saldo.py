"""Send to Saldo: a rental becomes a draft invoice in Saldo's data folder, in Saldo's format; sent again, it
updates that draft while it's still one."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from bodega.core import dates, money, pricing, sample
from bodega.core.store import Library
from bodega.services import saldo


@pytest.fixture
def saldo_home(tmp_path, monkeypatch):
    home = tmp_path / "Saldo"
    monkeypatch.setenv("SALDO_DATA_DIR", str(home))
    monkeypatch.setenv("COBRO_DATA_DIR", str(tmp_path / "Cobro"))
    return home


def _setup(home, *profiles):
    home.mkdir(parents=True, exist_ok=True)
    (home / "businesses.json").write_text(json.dumps(list(profiles)), encoding="utf-8")
    (home / "invoices").mkdir(exist_ok=True)


def _invoices(home) -> dict[str, dict]:
    return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in (home / "invoices").glob("*.json")}


def test_nothing_is_sent_before_saldo_has_been_opened_once(tmp_path, saldo_home):
    lib = sample.fill(Library(tmp_path / "b").load())
    assert not saldo.installed()
    with pytest.raises(OSError):
        saldo.send(lib, next(iter(lib.rentals.values())), lib.pricing(), {"id": "x"})
    assert not saldo_home.exists()  # nothing written before Saldo has been opened once


def test_cobros_files_wait_for_saldo_to_bring_them_over(tmp_path, saldo_home):
    cobro = tmp_path / "Cobro"
    cobro.mkdir()
    (cobro / "businesses.json").write_text("[]", encoding="utf-8")
    assert saldo.waiting_for_cobro()
    _setup(saldo_home, {"id": "biz1", "name": "Juniper Lane Films"})
    assert not saldo.waiting_for_cobro() and saldo.installed()


def test_draft_invoice_matches_the_rental(tmp_path, saldo_home):
    lib = sample.fill(Library(tmp_path / "b").load())
    r = next(iter(lib.rentals.values()))
    r.discount, r.tax_rate = "10", "8.25"
    b = lib.businesses.get(r.business_id) or lib.pricing()
    me = {"id": "biz1", "name": b.name, "prefix": "JL", "number_style": "year", "terms_days": 30}
    _setup(saldo_home, {"id": "other", "name": "Someone"}, me)
    year = dates.today().year
    (saldo_home / "invoices" / "old.json").write_text(
        json.dumps({"id": "old", "number": f"JL-{year}-007"}), encoding="utf-8"
    )
    number, updated = saldo.send(lib, r, b, me)
    assert number == f"JL-{year}-008" and not updated
    assert r.saldo_number == number and r.saldo_invoice in _invoices(saldo_home)
    inv = _invoices(saldo_home)[r.saldo_invoice]
    assert inv["id"] == r.saldo_invoice  # named by its id, as Saldo names its own
    assert inv["business_id"] == "biz1" and inv["status"] == "draft" and inv["terms_days"] == 30
    assert inv["auto_number"] is True
    assert inv["client"]["name"] == (r.client.company or r.client.name)
    # Saldo's math (qty × rate, minus the discount amount, plus tax %) gives the rental's total
    sub = sum((money.parse(i["qty"]) * money.parse(i["rate"]) for i in inv["items"]), Decimal(0))
    taxable = sub - money.parse(inv["discount"])
    total = money.cents(taxable + money.cents(taxable * money.parse(inv["tax_rate"]) / 100))
    assert total == pricing.totals(lib, r, b).total


def test_sending_again_updates_the_draft_and_keeps_what_saldo_changed(tmp_path, saldo_home):
    lib = sample.fill(Library(tmp_path / "b").load())
    r = next(iter(lib.rentals.values()))
    b = lib.businesses.get(r.business_id) or lib.pricing()
    me = {"id": "biz1", "name": b.name, "prefix": "JL"}
    _setup(saldo_home, me)
    number, _ = saldo.send(lib, r, b, me)
    inv = _invoices(saldo_home)[r.saldo_invoice]
    inv["payment"] = "Zelle to rentals@example.com"  # typed in Saldo
    inv["reminder"] = {"days": 7}  # a field this Bodega doesn't know
    (saldo_home / "invoices" / f"{r.saldo_invoice}.json").write_text(json.dumps(inv), encoding="utf-8")
    r.project = "Night Exterior Reshoot"
    again, updated = saldo.send(lib, r, b, me)
    invs = _invoices(saldo_home)
    assert updated and again == number and len(invs) == 1  # no second invoice
    inv = invs[r.saldo_invoice]
    assert inv["project"] == "Night Exterior Reshoot"
    assert inv["payment"] == "Zelle to rentals@example.com" and inv["reminder"] == {"days": 7}


def test_once_saldo_has_sent_it_a_new_draft_goes_beside_it(tmp_path, saldo_home):
    lib = sample.fill(Library(tmp_path / "b").load())
    r = next(iter(lib.rentals.values()))
    b = lib.businesses.get(r.business_id) or lib.pricing()
    me = {"id": "biz1", "name": b.name, "prefix": "JL"}
    _setup(saldo_home, me)
    first, _ = saldo.send(lib, r, b, me)
    path = saldo_home / "invoices" / f"{r.saldo_invoice}.json"
    inv = json.loads(path.read_text(encoding="utf-8"))
    inv["status"] = "sent"
    path.write_text(json.dumps(inv), encoding="utf-8")
    assert saldo.said(saldo.draft_of(r)) == f"sent {first}"
    second, updated = saldo.send(lib, r, b, me)
    assert not updated and second != first and len(_invoices(saldo_home)) == 2


def test_each_profile_sends_as_the_saldo_profile_it_was_given(tmp_path, saldo_home):
    lib = sample.fill(Library(tmp_path / "b").load())
    b = next(iter(lib.businesses.values()))
    one, two = {"id": "a", "name": "Juniper Lane Films"}, {"id": "b", "name": "Juniper Lane Films LLC"}
    assert saldo.profile_for([one], b) == one  # the only one
    assert saldo.profile_for([one, two], b) is None  # two: ask, never guess by name
    b.saldo_profile = "b"
    assert saldo.profile_for([one, two], b) == two
    again = Library(lib.root)
    lib.save_businesses()
    assert next(iter(again.load().businesses.values())).saldo_profile == "b"


def test_a_rental_pointing_at_an_odd_invoice_id_never_reads_outside_saldos_folder(tmp_path, saldo_home):
    lib = sample.fill(Library(tmp_path / "b").load())
    r = next(iter(lib.rentals.values()))
    _setup(saldo_home, {"id": "biz1"})
    r.saldo_invoice = "../../businesses"
    assert saldo.draft_of(r) is None


def test_send_to_saldo_from_the_window(qapp, data_folder, saldo_home, monkeypatch):
    from bodega.ui.dialogs import common
    from bodega.ui.window import transfer
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(sample.fill(Library(data_folder).load()))
    r = next(iter(w.lib.rentals.values()))
    _setup(saldo_home, {"id": "a", "name": "A", "prefix": "A"}, {"id": "b", "name": "B", "prefix": "B"})
    asked = []
    monkeypatch.setattr(transfer, "saldo_is_open", lambda: False)
    monkeypatch.setattr(common, "ask_choice", lambda _w, title, *a, **k: asked.append(title) or "b")
    monkeypatch.setattr(common, "confirm", lambda _w, title, *a, **k: asked.append(title) or True)
    w.send_to_saldo(r.id)
    assert asked == ["Which Saldo Profile Sends It?", f"Send {r.number} to Saldo?"]
    assert Library(data_folder).load().rentals[r.id].saldo_number.startswith("B-")
    asked.clear()
    w.send_to_saldo(r.id)  # remembered: no question about the profile, and it's an update
    assert asked == [f"Update Draft {r.saldo_number} in Saldo?"]
    monkeypatch.setattr(transfer, "saldo_is_open", lambda: True)
    shown = []
    monkeypatch.setattr(transfer, "notice", lambda _w, title, *a: shown.append(title))
    w.send_to_saldo(r.id)
    assert shown == ["Quit Saldo First"]
    w.close()


def test_an_open_saldo_is_found_without_being_told_anything(qapp):
    import getpass

    from PySide6.QtNetwork import QLocalServer
    from PySide6.QtTest import QTest

    from bodega.ui.window.transfer import saldo_is_open

    assert not saldo_is_open()
    server = QLocalServer()
    QLocalServer.removeServer(f"saldo-{getpass.getuser()}")
    assert server.listen(f"saldo-{getpass.getuser()}")
    heard = []
    server.newConnection.connect(lambda: heard.append(server.nextPendingConnection()))
    assert saldo_is_open()
    QTest.qWait(50)
    assert heard and not heard[0].bytesAvailable()  # Saldo's window stays where it is
    server.close()


def test_a_rental_says_where_its_invoice_stands_in_saldo(tmp_path, saldo_home):
    _setup(saldo_home, {"id": "p1", "name": "Juniper Lane Films", "prefix": "JLF", "terms_days": 15})
    lib = sample.fill(Library(tmp_path / "b").load())
    r = next(iter(lib.rentals.values()))
    assert saldo.where(r) == ""  # never sent
    number, _ = saldo.send(lib, r, lib.pricing(), {"id": "p1", "prefix": "JLF"})
    assert saldo.where(r) == f"Draft invoice {number} in Saldo, not sent yet."
    path = saldo_home / "invoices" / f"{r.saldo_invoice}.json"
    path.write_text(json.dumps({**json.loads(path.read_text(encoding="utf-8")), "status": "sent"}), encoding="utf-8")
    assert saldo.where(r) == f"Invoice {number} sent from Saldo."
    path.unlink()  # deleted in Saldo
    assert "isn't in Saldo any more" in saldo.where(r)


def test_zero_days_to_pay_stays_zero(tmp_path):
    lib = sample.fill(Library(tmp_path).load())
    r = next(iter(lib.rentals.values()))
    inv = saldo.invoice_for(lib, r, None, {"id": "p", "terms_days": 0}, [])
    assert inv["terms_days"] == 0  # due on receipt, not Saldo's 15
    assert saldo.invoice_for(lib, r, None, {"id": "p"}, [])["terms_days"] == saldo.TERMS_DAYS
