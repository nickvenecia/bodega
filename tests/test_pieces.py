"""A piece and the gear that goes with it, in the gear list (the standard's 4.3, G.11 and C-108): one row that opens in
place by its chevron; the gear under it one step in; the piece sums it up; its tick ticks all of it; search opens what
it finds; → ← and Return open and close; what's open is remembered; sorting keeps the gear under its piece."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest

from bodega.core import pricing, sample
from bodega.core.store import Library
from bodega.ui.window.tables import CHILD, GEAR_COL, ID, SUMMARY, TICK


@pytest.fixture
def win(qapp, data_folder, monkeypatch):
    from bodega.ui.window.main_window import MainWindow

    monkeypatch.setenv("BODEGA_REDUCE_MOTION", "1")  # (chevrons point at once; one test turns them)
    w = MainWindow(sample.fill(Library(data_folder).load()))
    w.show()
    w.go("gear")
    yield w
    w.close()


def piece(win, name: str):
    t = win.gear_table
    return next(r for r in t.item_rows() if r.text(GEAR_COL["name"]).startswith(name))


def chevron_at(t, row) -> QPoint:
    x = t.header().sectionViewportPosition(GEAR_COL["name"]) + t.name_shift(row) // 2
    return QPoint(x, t.visualItemRect(row).center().y())


def test_a_piece_opens_in_place_by_its_chevron_and_is_remembered(win, data_folder):
    from bodega.ui.window.main_window import MainWindow

    t = win.gear_table
    fx6 = piece(win, "Sony FX6")
    kids = [fx6.child(i) for i in range(fx6.childCount())]
    assert kids and all(k.data(0, CHILD) == fx6.data(0, ID) for k in kids)
    assert not fx6.isExpanded() and t.families  # closed at first; every name has room for a chevron
    assert t.name_shift(kids[0]) == t.name_shift(fx6) + 18  # the gear under it, one step in (G.11: 18)
    opened = fx6.data(0, ID)
    QTest.mouseClick(t.viewport(), Qt.MouseButton.LeftButton, pos=chevron_at(t, fx6))
    assert fx6.isExpanded() and opened in t.open_pieces and all(not k.isHidden() for k in kids)
    assert not t.ticked_ids()  # the chevron opens it, ticking nothing
    assert win.lib.settings["gear_open"] == [opened]
    win.refresh()
    fx6 = piece(win, "Sony FX6")
    assert fx6.isExpanded()  # a refill keeps it open
    win.close()
    again = MainWindow(Library(data_folder).load())
    again.go("gear")
    assert piece(again, "Sony FX6").isExpanded()  # and so does the next time
    again.close()


def test_a_click_on_the_piece_opens_it_on_the_right_and_its_gear_opens_its_own(win):
    t = win.gear_table
    fx6 = piece(win, "Sony FX6")
    t.open_piece(fx6, True)
    name = QPoint(t.header().sectionViewportPosition(GEAR_COL["name"]) + 120, t.visualItemRect(fx6).center().y())
    QTest.mouseClick(t.viewport(), Qt.MouseButton.LeftButton, pos=name)
    assert win.items.it.id == fx6.data(0, ID) and fx6.isExpanded()  # (the row opens the piece, not the fold)
    cage = fx6.child(0)
    QTest.mouseClick(t.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(name.x(), t.visualItemRect(cage).center().y()))
    assert win.items.it.id == cage.data(0, ID)
    t.open_piece(fx6, False)  # closing it over the open row opens the piece instead (as the Finder does)
    assert t.currentItem() is fx6 and win.items.it.id == fx6.data(0, ID)


def test_the_piece_sums_up_what_goes_with_it(win):
    from bodega.core import money

    t = win.gear_table
    lib, b = win.lib, win.lib.pricing()
    fx6 = piece(win, "Sony FX6")
    it = lib.items[fx6.data(0, ID)]
    n = fx6.childCount()
    assert fx6.data(0, SUMMARY) == f"{n} Attached"
    assert fx6.font(GEAR_COL["name"]).weight() >= 600  # its name in Semibold (G.11)
    everything = pricing.stock(lib, it, b)
    assert fx6.text(GEAR_COL["value"]) == money.fmt_short(money.whole(everything.value), "$")
    assert fx6.text(GEAR_COL["day"]) == money.fmt_short(pricing.item_rate(lib, it, b, it.qty), "$")
    # the group's divider still adds up each piece once
    group = fx6.parent()
    alone = pricing.Stock()
    for x, _u, _d in pricing.with_attached(lib, it):
        alone.add(pricing.stock(lib, x, b, attached=False))
    others = [group.child(i) for i in range(group.childCount()) if group.child(i) is not fx6]
    for o in others:
        alone.add(t.stocks[o.data(0, ID)])
        for k in range(o.childCount()):
            alone.add(t.stocks[o.child(k).data(0, ID)])
    assert group.text(GEAR_COL["qty"]) == f"{alone.pieces:,}"


def test_closed_it_shows_the_most_pressing_status_open_its_own(win):
    t = win.gear_table
    fx6 = piece(win, "Sony FX6")
    cage = win.lib.items[fx6.child(0).data(0, ID)]
    cage.status = "repair"
    win.lib.save_items()
    win.refresh()
    fx6 = piece(win, "Sony FX6")
    col = GEAR_COL["status"]
    assert fx6.text(col) == "1 in Repair" and cage.name in fx6.toolTip(col)
    t.open_piece(fx6, True)
    assert fx6.text(col) == "In"  # open, the piece's own (its gear says its own under it)
    t.open_piece(fx6, False)
    assert fx6.text(col) == "1 in Repair"


def test_its_tick_ticks_every_piece_under_it(win):
    t = win.gear_table
    fx6 = piece(win, "Sony FX6")
    family = {fx6.data(0, ID)} | {fx6.child(i).data(0, ID) for i in range(fx6.childCount())}
    box = QPoint(
        t.header().sectionViewportPosition(TICK) + t.columnWidth(TICK) // 2, t.visualItemRect(fx6).center().y()
    )
    QTest.mouseClick(t.viewport(), Qt.MouseButton.LeftButton, pos=box)
    assert set(t.ticked_ids()) == family and t.family_state(fx6) == "on"  # closed: ticked with it all the same
    fx6.child(0).setSelected(False)
    assert t.family_state(fx6) == "some"  # a dash
    QTest.mouseClick(t.viewport(), Qt.MouseButton.LeftButton, pos=box)
    assert t.family_state(fx6) == "on"
    QTest.mouseClick(t.viewport(), Qt.MouseButton.LeftButton, pos=box)
    assert not t.ticked_ids()


def test_keys_open_close_and_climb(win):
    t = win.gear_table
    fx6 = piece(win, "Sony FX6")
    t.setFocus()
    t.setCurrentItem(fx6)
    QTest.keyClick(t, Qt.Key.Key_Right)
    assert fx6.isExpanded()
    QTest.keyClick(t, Qt.Key.Key_Down)
    kid = t.currentItem()
    assert kid.parent() is fx6
    QTest.keyClick(t, Qt.Key.Key_Left)  # from the gear under it, up to the piece
    assert t.currentItem() is fx6 and fx6.isExpanded()
    QTest.keyClick(t, Qt.Key.Key_Left)
    assert not fx6.isExpanded()
    QTest.keyClick(t, Qt.Key.Key_Return)
    assert fx6.isExpanded()
    QTest.keyClick(t, Qt.Key.Key_Space)  # ticks it and all under it
    assert t.family_state(fx6) == "on"


def test_sorting_keeps_the_gear_under_its_piece(win):
    t = win.gear_table
    t.sortByColumn(GEAR_COL["name"], Qt.SortOrder.DescendingOrder)
    fx6 = piece(win, "Sony FX6")
    names = [fx6.child(i).text(GEAR_COL["name"]) for i in range(fx6.childCount())]
    assert names == sorted(names, key=str.casefold, reverse=True)  # sorted among themselves…
    assert all(fx6.child(i).data(0, CHILD) == fx6.data(0, ID) for i in range(fx6.childCount()))  # …never leaving
    t.sortByColumn(GEAR_COL["name"], Qt.SortOrder.AscendingOrder)
    names = [fx6.child(i).text(GEAR_COL["name"]) for i in range(fx6.childCount())]
    assert names == sorted(names, key=str.casefold)


def test_a_filter_opens_the_piece_whose_gear_it_finds(win):
    t = win.gear_table
    fx6 = piece(win, "Sony FX6")
    cage = win.lib.items[fx6.child(0).data(0, ID)]
    cage.status = "repair"
    win.lib.save_items()
    win.refresh()
    win.set_gear_filter("repair")
    fx6 = piece(win, "Sony FX6")
    assert t.shown == [cage.id] and fx6.isExpanded() and not fx6.isHidden()
    win.set_gear_filter("all")
    assert not piece(win, "Sony FX6").isExpanded()


def test_gear_under_a_piece_moves_with_it(win):
    t = win.gear_table
    fx6 = piece(win, "Sony FX6")
    t.open_piece(fx6, True)
    assert t._on_grip(QPoint(t.header().sectionViewportPosition(GEAR_COL["grip"]) + 4, t.visualItemRect(fx6.child(0)).center().y())) is None  # fmt: skip
    t.start_lift(fx6, t.visualItemRect(fx6).center().y())
    lift = t._lift
    assert lift.ids == [fx6.data(0, ID)]  # the piece is what moves…
    assert {r.data(0, ID) for r in lift.moving} == {fx6.data(0, ID)} | {
        fx6.child(i).data(0, ID) for i in range(fx6.childCount())
    }  # …with its gear
    t.end_lift(drop=False)
    said = []
    win.toast = lambda text, tone="": said.append(text)
    win.step_gear(-1, [fx6.child(0).data(0, ID)])
    assert said and "with its piece" in said[0]


def test_the_chevron_turns_and_everything_paints(win, monkeypatch):
    t = win.gear_table
    fx6 = piece(win, "Sony FX6")
    monkeypatch.setenv("BODEGA_REDUCE_MOTION", "0")
    t.open_piece(fx6, True)
    assert 0 <= t.angle(fx6) < 90 and fx6.data(0, ID) in t._turns  # on its way
    monkeypatch.setenv("BODEGA_REDUCE_MOTION", "1")
    t.open_piece(fx6, False)
    assert t.angle(fx6) == 0 and fx6.data(0, ID) not in t._turns  # Reduce Motion: it just points

    def shot() -> QImage:
        img = QImage(t.viewport().size(), QImage.Format.Format_ARGB32)
        img.fill(0)
        t.viewport().render(img)
        r = t.visualItemRect(fx6)
        x = t.header().sectionViewportPosition(GEAR_COL["name"])
        return img.copy(x, r.top(), t.name_shift(fx6), r.height())  # where its chevron is

    closed = shot()
    t.open_piece(fx6, True)
    t.viewport().repaint()
    assert shot() != closed  # it points down now


def test_goes_with_shows_only_where_the_row_under_its_piece_doesnt_say_it(win):
    t = win.gear_table
    lib = win.lib
    fx6 = piece(win, "Sony FX6")
    cage = lib.items[fx6.child(0).data(0, ID)]
    battery = next(i for i in lib.items.values() if i.name.startswith("Mini V-Mount"))
    assert not t.any_with
    assert lib.attach([battery.id], cage.id) == 1  # gear on gear that goes with the FX6
    win.refresh()
    fx6 = piece(win, "Sony FX6")
    row = next(fx6.child(i) for i in range(fx6.childCount()) if fx6.child(i).data(0, ID) == battery.id)
    assert row.data(0, CHILD) == fx6.data(0, ID)  # still one level under the FX6 (one level deep)…
    assert row.text(GEAR_COL["with"]) == cage.name and t.any_with  # …and Goes With says it's on the cage
