"""Regressions: each test is a bug that was found and fixed, so it stays fixed."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from bodega.core import importer, money, pricing, sample
from bodega.core.model import MAX_QTY, Item, clamp_qty
from bodega.core.store import Library


@pytest.fixture
def lib(data_folder):
    return sample.fill(Library(data_folder).load())


@pytest.fixture
def win(qapp, data_folder):
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(sample.fill(Library(data_folder).load()))
    w.show()
    yield w
    w.close()


def _totals(lib):
    return {r.id: pricing.totals(lib, r, lib.businesses.get(r.business_id)).total for r in lib.rentals.values()}


# Core
def test_deleting_gear_or_kits_keeps_rental_prices(lib):
    before = _totals(lib)
    for r in list(lib.rentals.values()):
        for ln in r.lines:
            if ln.kind == "package":
                lib.delete_package(ln.ref)
            elif ln.kind == "item":
                lib.delete_items([ln.ref])
    assert _totals(lib) == before
    again = Library(lib.root).load()  # and it was saved that way
    assert _totals(again) == before


def test_huge_numbers_are_typos_not_crashes():
    assert money.parse("9" * 30) == 0
    assert money.parse("$1,200.50") == Decimal("1200.50")
    assert money.cents(Decimal("1e40")) == 0
    assert importer._number("9" * 30) is None


def test_a_quantity_is_always_a_sensible_whole_number():
    assert clamp_qty("25000") == MAX_QTY
    assert clamp_qty(float("inf")) == 1
    assert clamp_qty("abc") == 1
    assert Item.from_dict({"name": "x", "qty": 1e400}).qty == 1


def test_csv_keeps_line_breaks_in_notes(tmp_path):
    a = Item(name="Light", notes="line one\nline two")
    path = importer.write_csv([a], {a.id: a}, tmp_path / "gear.csv")
    back = importer.read(path).items
    assert back[0].notes == "line one\nline two"


def test_broken_records_are_skipped_and_kept(data_folder):
    data_folder.mkdir(parents=True, exist_ok=True)
    (data_folder / "packages.json").write_text(json.dumps([{"name": "Good"}, {"name": "Bad", "lines": 5}]))
    (data_folder / "rentals").mkdir()
    (data_folder / "rentals" / "r1.json").write_text(json.dumps({"lines": 5}))
    lib = Library(data_folder).load()  # doesn't crash
    assert [p.name for p in lib.packages.values()] == ["Good"]
    kept = [p.name for p in data_folder.iterdir()] + [p.name for p in (data_folder / "rentals").iterdir()]
    assert any(n.startswith("packages.json.partly-unreadable") for n in kept)
    assert any(n.startswith("r1.json.unreadable") for n in kept) and "r1" not in lib.rentals


def test_gear_file_of_the_wrong_shape_is_not_overwritten(data_folder):
    data_folder.mkdir(parents=True, exist_ok=True)
    (data_folder / "gear.json").write_text(json.dumps({"oops": "a dict"}))
    lib = Library(data_folder).load()
    lib.save_items()
    assert any(p.name.startswith("gear.json.unreadable") for p in data_folder.iterdir())


def test_ids_that_could_name_other_files_are_replaced(data_folder):
    data_folder.mkdir(parents=True, exist_ok=True)
    (data_folder / "gear.json").write_text(json.dumps([{"id": "../../evil", "name": "x"}]))
    lib = Library(data_folder).load()
    assert all("/" not in i and ".." not in i for i in lib.items)


def test_belongs_to_loops_are_broken(data_folder):
    a, b = Item(name="A"), Item(name="B")
    a.parent, b.parent = b.id, a.id
    lib = Library(data_folder).load()
    lib.items = {a.id: a, b.id: b}
    lib.untangle()
    assert not (a.parent and b.parent)


# Window
def test_emptied_group_goes_back_to_all_gear(win):
    it = next(iter(win.lib.items.values()))
    win.lib.put_in_group([it.id], "Solo")
    win.refresh()
    win.go("grp:Solo")
    win.open("gear", it.id)
    win.move_gear([it.id], "Lenses")
    assert win.view_key == "gear"


def test_esc_lets_go_of_a_rental(win):
    r = next(iter(win.lib.rentals.values()))
    win.open("rentals", r.id)
    win.deselect()
    assert win.rentals.r is None


def test_opening_something_deleted_does_nothing(win):
    fx6 = next(i for i in win.lib.items.values() if i.name.startswith("Sony FX6"))
    win.open("gear", fx6.id)
    win.open("gear", "gone-id")
    assert win.items.it is fx6


def test_kit_row_stays_picked_after_an_edit(win):
    kit = next(iter(win.lib.packages.values()))
    win._place_picked(f"kit:{kit.id}")
    win.refresh()
    assert win.sidebar.rows[f"kit:{kit.id}"].property("selected")


def test_return_cant_be_before_pickup(win):
    r = next(iter(win.lib.rentals.values()))
    win.open("rentals", r.id)
    p = win.rentals
    assert p.ret.minimumDate() == p.pickup.date()
