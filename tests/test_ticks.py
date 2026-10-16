"""Ticks on every list and the selection bar (the standard's 4.3, 4.17, G.10.3, G.10.7, G.10.11): a click opens a row
and never ticks it; its tick, ⌘-click or Space ticks; Shift-click ticks a run; the heading's tick ticks every row
showing; ticks last through a refill and go with a new place, search or filter; the bar says how many and acts on
all of them."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from bodega.core import sample
from bodega.core.store import Library
from bodega.ui.window.tables import ID, TICK

CMD, SHIFT = Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.ShiftModifier


@pytest.fixture
def win(qapp, data_folder):
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(sample.fill(Library(data_folder).load()))
    w.show()
    yield w
    w.close()


def at(t, row, col: int) -> QPoint:
    r = t.visualItemRect(row)
    x = t.header().sectionViewportPosition(col) + t.columnWidth(col) // 2
    return QPoint(x, r.center().y())


def rows(t):
    return [r for r in t.showing_rows() if r.data(0, ID)]


def test_a_click_opens_a_row_and_its_tick_ticks_it(win):
    win.go("gear")
    t = win.gear_table
    first, second = rows(t)[:2]
    QTest.mouseClick(t.viewport(), Qt.MouseButton.LeftButton, pos=at(t, first, t.NAME_COL))
    assert win.items.it.id == first.data(0, ID) and not t.selectedItems()  # open, not ticked
    QTest.mouseClick(t.viewport(), Qt.MouseButton.LeftButton, pos=at(t, second, TICK))
    assert t.ticked_ids() == [second.data(0, ID)] and win.items.it.id == first.data(0, ID)  # the open one stays
    QTest.mouseClick(t.viewport(), Qt.MouseButton.LeftButton, pos=at(t, second, TICK))
    assert t.ticked_ids() == []  # its tick again: unticked


def test_cmd_click_space_and_shift_click_tick(win):
    win.go("gear")
    t = win.gear_table
    r = rows(t)
    QTest.mouseClick(t.viewport(), Qt.MouseButton.LeftButton, CMD, at(t, r[0], t.NAME_COL))
    assert t.ticked_ids() == [r[0].data(0, ID)]
    QTest.mouseClick(t.viewport(), Qt.MouseButton.LeftButton, SHIFT, at(t, r[2], t.NAME_COL))
    assert set(t.ticked_ids()) >= {r[0].data(0, ID), r[1].data(0, ID), r[2].data(0, ID)}  # a run
    t.clearSelection()
    t.setFocus()
    t.setCurrentItem(r[1])
    QTest.keyClick(t, Qt.Key.Key_Down)  # an arrow moves to the next row (it opens), ticking nothing
    assert t.currentItem() is r[2] and not t.ticked_ids() and win.items.it.id == r[2].data(0, ID)
    QTest.keyClick(t, Qt.Key.Key_Space)
    assert t.ticked_ids() == [r[2].data(0, ID)]


def test_the_headings_tick_ticks_every_row_showing(win):
    win.go("gear")
    t = win.gear_table
    assert t.tick_state() == "off"
    head = t.header()
    x = head.sectionViewportPosition(TICK) + t.columnWidth(TICK) // 2
    QTest.mouseClick(head.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(x, head.height() // 2))
    assert t.tick_state() == "on" and len(t.ticked_ids()) == len(rows(t))
    rows(t)[0].setSelected(False)
    assert t.tick_state() == "some"  # a dash: some are
    QTest.mouseClick(head.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(x, head.height() // 2))
    assert t.tick_state() == "on"
    QTest.mouseClick(head.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(x, head.height() // 2))
    assert t.tick_state() == "off"


def test_ticks_last_through_a_refill_and_go_with_a_search(win):
    win.go("gear")
    t = win.gear_table
    a, b = rows(t)[:2]
    keep = {a.data(0, ID), b.data(0, ID)}
    a.setSelected(True)
    b.setSelected(True)
    win.refresh()  # (every edit refills the list)
    assert set(t.ticked_ids()) == keep
    win.search.setText("sony")
    assert t.ticked_ids() == []  # a tick never holds a row you can't see
    win.search.clear()
    rows(t)[0].setSelected(True)
    win.go("kits")
    win.go("gear")
    assert t.ticked_ids() == []  # nor one in another place


def test_the_selection_bar_says_how_many_and_deletes_them_all(win):
    win.go("gear")
    t = win.gear_table
    free = [r for r in rows(t) if not win.lib.rentals_with(r.data(0, ID))][:3]
    for r in free:
        r.setSelected(True)
    bar = win.selbar
    assert bar.isVisibleTo(win) and bar.count.text() == "3 Selected"
    assert bar.buttons["move"].isVisibleTo(bar) and bar.buttons["delete"].isVisibleTo(bar)
    foot = win.pages.mapTo(win, win.pages.rect().bottomLeft()).y()
    assert bar.geometry().bottom() < foot  # over the list's foot
    win.toast("Saved.")
    assert win.toaster.geometry().top() + win.toaster._pill.bottom() < bar.geometry().top()  # a toast rises above it
    ids = [r.data(0, ID) for r in free]
    bar.buttons["delete"].click()
    QTest.qWait(50)  # (once the click is over)
    assert not any(i in win.lib.items for i in ids) and win.toaster._action_word == "Undo"
    assert not bar.isVisibleTo(win)  # nothing ticked: it goes
    pill_foot = win.toaster.geometry().top() + win.toaster._pill.bottom()  # (its shadow reaches further)
    assert pill_foot <= win.pages.mapTo(win, win.pages.rect().bottomLeft()).y()


def test_the_bars_cross_unticks_and_move_to_group_moves_them(win):
    win.go("gear")
    t = win.gear_table
    r = rows(t)[:2]
    for x in r:
        x.setSelected(True)
    ids = [x.data(0, ID) for x in r]
    group = win.lib.groups()[-1]
    win._fill_move_menu()
    move = next(a for a in win._move_menu.actions() if a.text() == group)
    move.trigger()
    QTest.qWait(50)
    assert all(win.lib.items[i].group == group for i in ids)
    win.selbar.close.click()
    QTest.qWait(50)
    assert t.ticked_ids() == [] and not win.selbar.isVisibleTo(win)


def test_rentals_bar_deletes_only_the_quotes_and_says_how_many(win):
    from bodega.core.model import Rental

    lib = win.lib
    b = next(iter(lib.businesses.values()))
    q = lib.new_rental(b)  # a quote
    booked = next(r for r in lib.rentals.values() if r.id != q.id)
    booked.status = "booked"
    lib.save_rental(booked)
    win.go("rentals")
    t = win.rental_table
    for row in rows(t):
        row.setSelected(row.data(0, ID) in (q.id, booked.id))
    assert win.selbar.buttons["delete"].text() == "Delete 1 Quote"  # not all of them can go: it says how many
    win.selbar.buttons["delete"].click()
    QTest.qWait(50)
    assert q.id not in lib.rentals and booked.id in lib.rentals  # a booked one is never deleted
    assert isinstance(lib.rentals[booked.id], Rental)
