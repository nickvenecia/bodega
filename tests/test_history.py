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
    number = lib.rentals[r].number
    lib.delete_rental(r)
    h.mark()
    assert h.undo() == f"Delete {number}"  # named for what was done…
    assert h.shown == ("rentals", r)  # …and what came back is the one to show
    assert r in lib.rentals and r in Library(tmp_path).load().rentals
    assert h.undo() == "Change to Changed"
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
    assert win.act_undo.text() == "Undo Change to Renamed" and win.act_undo.isEnabled()
    win.undo()
    win._edit_menu_state()
    assert win.act_redo.text() == "Redo Change to Renamed"
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


def test_undo_names_what_was_done(tmp_path):
    from bodega.core.history import action, state_of

    lib = sample.fill(Library(tmp_path).load())
    before = state_of(lib)
    gone = [i for i in lib.items.values() if not lib.rentals_with(i.id)][:3]
    lib.delete_items([i.id for i in gone])
    assert action(before, state_of(lib))[0] == "Delete 3 Pieces"  # (its kits changing too follows from it)
    one = state_of(lib)
    it = next(iter(lib.items.values()))
    it.name = "A Very Long Name For A Piece Of Camera Gear"
    what, about = action(one, state_of(lib))
    assert what.startswith("Change to A Very Long") and what.endswith("…") and about == ("gear", it.id)
