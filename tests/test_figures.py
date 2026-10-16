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
    from bodega.ui.components.widgets import widgets_of

    first = widgets_of(chips.lay)[0]
    assert first is chips.clear_all and first.height() == chips.chips[0].height()
    divide = win.view_menu.divide
    QTest.mouseClick(chips.clear_all, Qt.MouseButton.LeftButton)
    QTest.qWait(50)
    assert not win.view_menu.filter.active() and not chips.isVisibleTo(win) and win.view_menu.divide == divide


def test_a_pieces_strip_has_its_day_rate_what_it_earned_and_how_much_is_paid_off(data_folder):
    from decimal import Decimal

    from bodega.core.earnings import Earned

    lib = sample.fill(Library(data_folder).load())
    b = lib.pricing()
    it = next(i for i in lib.items.values() if i.rentable and float(i.value or 0) > 0)
    plain = by_key(figures.piece(lib, it, b, None))
    assert set(plain) == {"rate"}  # nothing earned yet: no earnings, no share of its cost
    f = by_key(figures.piece(lib, it, b, Earned(amount=Decimal("100.40"), rentals={"r1"})))
    assert f["earned"].value == "$100" and f["earned"].label == "Earned, 1 Rental" and "estimate" in f["earned"].tip
    assert f["payoff"].label == "Paid Off" and f["payoff"].value.endswith("%")
    paid_back = by_key(figures.piece(lib, it, b, Earned(amount=Decimal(10**6), rentals={"a", "b"})))
    assert paid_back["payoff"].label == "Paid for Itself" and paid_back["payoff"].tone == "good"
    booked = by_key(figures.piece(lib, it, b, Earned(coming=Decimal(50))))
    assert booked["earned"].label == "Booked" and "payoff" not in booked
    it.rentable = False
    assert "rate" not in by_key(figures.piece(lib, it, b, None))  # not for rent: no day rate


def test_the_strips_sit_under_the_heads_divided_by_hairlines(win):
    from bodega.ui.window.tables import ID

    win.go("gear")
    row = next(r for r in win.gear_table.showing_rows() if r.data(0, ID))
    win.open("gear", row.data(0, ID))
    strip = win.items.strip
    assert strip.isVisibleTo(win.items) and strip.cells[0][3].text() == "Day Rate"
    assert strip.geometry().top() > win.items.name.geometry().top()
    shown = [c for c in strip.cells if c[1].isVisibleTo(strip)]
    assert all(line.isVisibleTo(strip) == (n > 0) for n, (line, *_r) in enumerate(shown))  # between figures only
    assert "rate" not in win.items.sum_rows  # a fact once on a record: the card no longer repeats it
    kit_id = next(iter(win.lib.packages))
    win.go("kits")
    win.open("packages", kit_id)
    labels = [c[3].text() for c in win.packages.strip.cells if c[1].isVisibleTo(win.packages.strip)]
    assert labels == ["Day Rate", "Week", "Pieces"]


def test_a_rental_has_a_head_its_renter_number_status_and_strip(win):
    lib = win.lib
    r = next(iter(lib.rentals.values()))
    win.go("rentals")
    win.open("rentals", r.id)
    p = win.rentals
    who = r.client.company or r.client.name
    assert p.head_name.text() == who and p.head_number.text() == r.number
    assert p.head_state.text() in ("Quote", "Booked", "Out", "Late", "Returned", "Cancelled")
    assert r.project in p.head_detail.text()
    labels = [c[3].text() for c in p.strip.cells if c[1].isVisibleTo(p.strip)]
    assert labels[0] == "Total" and "Pieces" in labels
    assert p.head_name.geometry().top() < p.strip.geometry().top()


def test_a_narrow_strip_narrows_its_gaps_then_leaves_the_last_figures_out(qapp):
    from bodega.core.figures import Figure
    from bodega.ui.components.figures import FigureStrip
    from bodega.ui.style import tokens

    s = FigureStrip()
    s.show_for([Figure(k, f"Label {k}", "$12,345") for k in "abcd"])
    s.resize(2000, 60)
    s.show()
    shown = lambda: [c for c in s.cells if not c[1].isHidden()]
    assert len(shown()) == 4 and shown()[1][1].layout().contentsMargins().left() == tokens.STRIP_PAD
    s.resize(300, 60)  # (four don't fit at the narrowest gap)
    assert 1 <= len(shown()) < 4 and shown()[0][3].text() == "Label a"  # the first, most important, stays
    for _line, cell, _value, _label in shown()[1:]:
        assert cell.layout().contentsMargins().left() >= tokens.STRIP_PAD_MIN
    s.deleteLater()
