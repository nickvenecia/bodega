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


def test_undo_says_what_it_would_change_back(qapp, data_folder):
    from bodega.ui.window.main_window import MainWindow

    win = MainWindow(sample.fill(Library(data_folder).load()))
    win._edit_menu_state()
    assert win.act_undo.text() == "Undo" and not win.act_undo.isEnabled()
    it = next(iter(win.lib.items.values()))
    it.name = "Renamed"
    win._item_edited(it)
    win.flush()
    win._edit_menu_state()
    assert win.act_undo.text() == "Undo Change to Gear" and win.act_undo.isEnabled()
    win.undo()
    win._edit_menu_state()
    assert win.act_redo.text() == "Redo Change to Gear"
    win.close()


def test_undo_steps_share_what_didnt_change(data_folder):
    lib = sample.fill(Library(data_folder).load())
    h = History(lib)
    first, second = list(lib.items.values())[:2]
    first.name = "Changed Once"
    h.mark()
    second.name = "Changed Twice"
    h.mark()
    a, b = h.undos[-1]["items"], h.last["items"]
    same = [x for x in a if x["id"] not in (first.id, second.id)]
    assert same and all(any(x is y for y in b) for x in same)  # one copy of each unchanged piece, shared
    assert h.undo() and lib.items[second.id].name != "Changed Twice"
