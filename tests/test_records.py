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
