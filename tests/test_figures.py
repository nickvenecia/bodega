"""The figure row above each list (the standard's 4.3, G.10.5, core/figures.py): three or four figures about the
whole list, the same whatever the search hides; a figure that's a slice filters the list when pressed, and lets go
pressed again."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from bodega.core import figures, sample
from bodega.core.store import Library


def by_key(fs):
    return {f.key: f for f in fs}


def test_gear_figures_count_every_unit_and_leave_retired_gear_out(data_folder):
    lib = sample.fill(Library(data_folder).load())
    f = by_key(figures.gear(lib))
    live = [i for i in lib.items.values() if not i.is_retired()]
    assert f["pieces"].value == f"{sum(i.qty for i in live):,}"
    assert f["out"].slice == "out" and f["repair"].slice == "repair" and not f["value"].slice  # a sum is plain
    assert f["repair"].tone == "" and f["value"].value.startswith("$")  # a zero is never coloured
    it = live[0]
    lib.retire([it.id])
    assert by_key(figures.gear(lib))["pieces"].value == f"{sum(i.qty for i in live[1:]):,}"


def test_in_repair_is_a_warning_and_late_is_bad_only_when_there_are_some(data_folder):
    lib = sample.fill(Library(data_folder).load())
    it = next(i for i in lib.items.values() if not i.is_retired())
    it.status = "repair"
    f = by_key(figures.gear(lib))
    assert f["repair"].value == "1" and f["repair"].tone == "warn"
    r = by_key(figures.rentals(lib))
    assert r["late"].tone == ("bad" if r["late"].value != "0" else "")
    assert r["out"].slice == "out" and r["upcoming"].slice == "upcoming" and not r["quotes"].slice


def test_a_groups_figures_are_that_groups(data_folder):
    lib = sample.fill(Library(data_folder).load())
    group = lib.groups()[0]
    mine = [i for i in lib.items.values() if i.group == group and not i.is_retired()]
    assert by_key(figures.gear(lib, group))["pieces"].value == f"{sum(i.qty for i in mine):,}"


def test_kit_figures(data_folder):
    lib = sample.fill(Library(data_folder).load())
    f = by_key(figures.kits(lib))
    assert f["kits"].value == f"{len(lib.packages):,}" and f["rate"].value.startswith("$")


@pytest.fixture
def win(qapp, data_folder):
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(sample.fill(Library(data_folder).load()))
    w.show()
    yield w
    w.close()


def tile(win, key_label: str):
    return next(t for t in win.figure_row.tiles if t.isVisibleTo(win) and t.label.text() == key_label)


def test_the_row_shows_on_every_list_but_the_calendar(win):
    for place, first in (("gear", "Pieces"), ("kits", "Kits"), ("rentals", "Out Now")):
        win.go(place)
        assert win.figure_row.isVisibleTo(win) and win.figure_row.tiles[0].label.text() == first
    win.go("calendar")
    assert not win.figure_row.isVisibleTo(win)
    win.go("gear")
    shown = tile(win, "Pieces").value.text()
    win.search.setText("sony")
    assert tile(win, "Pieces").value.text() == shown  # about the whole list, whatever the search hides


def test_pressing_a_slice_filters_the_list_and_again_lets_go(win):
    win.go("gear")
    t = tile(win, "In Repair")
    assert t.focusPolicy() == Qt.FocusPolicy.TabFocus and t.accessibleName().startswith("In Repair: ")
    QTest.mouseClick(t, Qt.MouseButton.LeftButton)
    QTest.qWait(50)  # (once the click is over)
    assert win.view_menu.filter.show == "repair" and tile(win, "In Repair").property("on") is True
    assert win.filter_chips.isVisibleTo(win)  # the filter it turned on is said, with its ✕
    t = tile(win, "In Repair")
    t.setFocus()
    QTest.keyClick(t, Qt.Key.Key_Space)  # the keyboard does what a click does
    QTest.qWait(50)
    assert win.view_menu.filter.show == "all" and tile(win, "In Repair").property("on") is False
    plain = tile(win, "Pieces")
    assert plain.focusPolicy() == Qt.FocusPolicy.NoFocus
    QTest.mouseClick(plain, Qt.MouseButton.LeftButton)
    QTest.qWait(50)
    assert win.view_menu.filter.show == "all"  # a sum does nothing


def test_a_rentals_slice_goes_to_its_place(win):
    win.go("rentals")
    QTest.mouseClick(tile(win, "Coming Up"), Qt.MouseButton.LeftButton)
    QTest.qWait(50)
    assert win.view_key == "upcoming" and tile(win, "Coming Up").property("on") is True
    QTest.mouseClick(tile(win, "Coming Up"), Qt.MouseButton.LeftButton)
    QTest.qWait(50)
    assert win.view_key == "rentals"


def test_the_filter_chips_sit_above_the_figures_with_clear_all_first(win):
    win.go("gear")
    win.view_menu.filter.company = "Sony"
    win.set_gear_filter("repair")
    chips = win.filter_chips
    assert chips.isVisibleTo(win) and [c.text() for c in chips.chips] == ["In Repair", "Sony"]
    assert chips.geometry().bottom() < win.figure_row.geometry().top()  # (G.10.6) under the title, above the figures
    first = chips.lay.itemAt(0).widget()
    assert first is chips.clear_all and first.height() == chips.chips[0].height()
    divide = win.view_menu.divide
    QTest.mouseClick(chips.clear_all, Qt.MouseButton.LeftButton)
    QTest.qWait(50)
    assert not win.view_menu.filter.active() and not chips.isVisibleTo(win) and win.view_menu.divide == divide
