"""Undo and redo (core/history.py)."""

from __future__ import annotations

from bodega.core import sample
from bodega.core.history import History
from bodega.core.store import Library


def test_undo_redo_round_trip(tmp_path):
    lib = sample.fill(Library(tmp_path).load())
    h = History(lib)
    assert not h.can_undo() and h.undo() is None
    first = next(iter(lib.items.values()))
    old = first.name
    first.name = "Changed"
    h.mark()
    r = next(iter(lib.rentals))
    lib.delete_rental(r)
    h.mark()
    assert h.undo() == "rentals"
    assert r in lib.rentals and r in Library(tmp_path).load().rentals
    assert "gear" in h.undo()
    assert lib.items[first.id].name == old
    assert h.undo() is None
    h.redo()
    assert lib.items[first.id].name == "Changed"
    h.redo()
    assert r not in lib.rentals and r not in Library(tmp_path).load().rentals
    assert h.redo() is None


def test_a_change_taken_back_leaves_no_step(tmp_path):
    lib = sample.fill(Library(tmp_path).load())
    h = History(lib)
    it = next(iter(lib.items.values()))
    it.notes = "x"
    h.mark()
    it.notes = ""
    h.mark()
    assert not h.undos


def test_saving_alone_is_not_a_change(tmp_path):
    lib = sample.fill(Library(tmp_path).load())
    h = History(lib)
    lib.save_rental(next(iter(lib.rentals.values())))  # stamps "updated"
    assert not h.mark()
