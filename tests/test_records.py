"""What stays on record: each rental's history, cancelling instead of deleting, retiring gear rentals point to,
and booking gear that's already promised (asked first)."""

from __future__ import annotations

from PySide6.QtTest import QTest

from bodega.core import sample
from bodega.core.model import RentalLine
from bodega.core.store import Library


def _lib(folder) -> Library:
    return sample.fill(Library(folder).load())


def test_a_rentals_history_is_written_as_it_changes(data_folder):
    lib = _lib(data_folder)
    b = next(iter(lib.businesses.values()))
    r = lib.new_rental(b)
    assert [e.what for e in r.history] == ["Made as a quote"]
    r.status = "booked"
    lib.save_rental(r)
    was = r.number
    r.number = "JLF-OLD-17"
    lib.save_rental(r)
    r.status = "cancelled"
    lib.save_rental(r)
    again = Library(data_folder).load().rentals[r.id]
    assert [e.what for e in again.history] == [
        "Made as a quote",
        "Booked",
        f"Number changed from {was} to JLF-OLD-17",
        "Cancelled",
    ]
    assert all(e.at for e in again.history)


def test_saving_without_a_change_adds_nothing(data_folder):
    lib = _lib(data_folder)
    r = next(iter(lib.rentals.values()))
    n = len(r.history)
    lib.save_rental(r)
    lib.save_rental(r)
    assert len(r.history) == n


def test_a_copy_starts_its_own_history(data_folder):
    lib = _lib(data_folder)
    src = next(iter(lib.rentals.values()))
    src.saldo_invoice, src.saldo_number = "abc123", "JL-2026-004"
    copy = lib.duplicate_rental(src)
    assert [e.what for e in copy.history] == [f"Made as a quote, from {src.number}"]
    assert not copy.saldo_invoice and not copy.checks and not copy.checked_out


def test_only_a_quote_can_be_deleted():
    from bodega.core.model import Rental

    assert Rental(status="quote").deletable()
    assert not any(Rental(status=s).deletable() for s in ("booked", "out", "returned", "cancelled"))


def test_rentals_with_a_piece_counts_kits_too(data_folder):
    lib = _lib(data_folder)
    kit = next(iter(lib.packages.values()))
    inside = kit.lines[0].item_id
    for r in lib.rentals.values():
        r.lines = [RentalLine("package", kit.id, 1)]
    assert lib.rentals_with(inside)


def test_booking_gear_thats_already_promised_asks_first(qapp, data_folder, monkeypatch):
    from bodega.ui.window import editing
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(_lib(data_folder))
    booked = next(iter(w.lib.rentals.values()))
    assert booked.status == "booked"
    r = w.lib.duplicate_rental(booked)  # the same gear, the same dates: short
    w.refresh()
    w.open("rentals", r.id)
    asked, answer = [], [False]
    monkeypatch.setattr(editing, "confirm", lambda _w, title, *a, **k: asked.append(title) or answer[0])
    panel = w.rentals
    i = panel.status.findData("booked")
    panel.status.setCurrentIndex(i)  # picked from the dropdown
    QTest.qWait(20)
    assert asked == [f"Book {r.number} Anyway?"] and r.status == "quote"
    assert panel.status.currentData() == "quote"  # said no: it stays a quote
    answer[0] = True
    panel.status.setCurrentIndex(i)
    QTest.qWait(20)
    assert r.status == "booked" and len(asked) == 2
    w.close()


def test_attaching_copies_the_department_and_group_and_never_makes_a_loop(data_folder):
    from bodega.core.model import Item

    lib = _lib(data_folder)
    cam = next(i for i in lib.items.values() if i.name.startswith("Sony FX6"))
    plate = lib.add_item(Item(name="Quick Release Plate", department="Grip", group="Plates"))
    assert lib.attach([plate.id], cam.id) == 1
    plate = Library(data_folder).load().items[plate.id]
    assert (plate.parent, plate.department, plate.group) == (cam.id, cam.department, cam.group)
    assert lib.attach([cam.id], plate.id) == 0  # the camera can't go with what goes with it
    lib.detach(plate.id)
    assert not lib.items[plate.id].parent and lib.items[plate.id].group == cam.group


def test_marking_a_rental_out_and_back_stamps_it_and_writes_its_history(data_folder):
    lib = _lib(data_folder)
    r = next(iter(lib.rentals.values()))
    lib.set_status(r, "out")
    assert r.checked_out and not r.checked_in
    lib.set_status(r, "returned")
    again = Library(data_folder).load().rentals[r.id]
    assert again.checked_in and [e.what for e in again.history][-2:] == ["Marked out", "Marked returned"]


def test_an_import_keeps_a_copy_first_and_takes_the_sheets_pricing_only_when_asked(data_folder):
    from bodega.core.model import Item

    lib = _lib(data_folder)
    b = next(iter(lib.businesses.values()))
    rate = b.rate_pct
    lib.import_items([Item(name="Astera Titan Tube")], None, b)
    assert b.rate_pct == rate and list((data_folder / "backups").glob("Bodega * before-import.zip"))
    lib.import_items([Item(name="Astera Helios Tube")], ("5", "9"), b)
    assert (b.rate_pct, b.value_tax) == ("5", "9")


def test_a_rentals_status_is_worded_in_one_place():
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "bodega"
    copies = [
        str(f.relative_to(root))
        for f in root.rglob("*.py")
        if re.search(r'"quote":\s*"Quote"', f.read_text(encoding="utf-8"))
    ]
    assert copies == ["core/model.py"], copies  # model.RENTAL_WORDS: every list, panel and page reads it


def test_the_main_button_comes_from_one_helper():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "bodega" / "ui"
    by_hand = [
        str(f.relative_to(root))
        for f in root.rglob("*.py")
        if 'setObjectName("Primary")' in f.read_text(encoding="utf-8")
    ]
    assert by_hand == ["components/widgets.py"], by_hand  # widgets.primary_button() everywhere else
