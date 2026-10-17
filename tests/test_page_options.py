"""Page options (the standard's C-53 and C-61): paper, letterhead and a note on every page; a list's columns (ticked,
in order) and filters (a column and a value, or a From and a To); kept as your last choice for each kind of page,
and as a profile's default; every change redraws the pages."""

from __future__ import annotations

import pytest

from bodega.core import document, pageopts, sample
from bodega.core.model import Item
from bodega.core.store import Library
from bodega.doc import render


@pytest.fixture
def lib(data_folder):
    return sample.fill(Library(data_folder).load())


def test_options_read_safely_and_the_name_column_always_prints():
    o = pageopts.PageOptions.from_dict(
        {"paper": "tabloid", "letterhead": "no", "note": 5, "columns": ["value", "nope", "qty"], "filters": [1, {"col": "x"}]}
    )  # fmt: skip
    assert (o.paper, o.letterhead, o.note, o.filters) == ("letter", True, "", [])  # odd values: the defaults
    assert pageopts.columns("inventory", o) == ["gear", "value", "qty"]  # (unknown ones left out, Gear always in)
    assert pageopts.columns("ratecard", pageopts.PageOptions()) == pageopts.RATECARD_SHOWN
    assert pageopts.PageOptions(paper="a4").size == pageopts.PAPERS["a4"][1]


def test_names_and_numbers_sort_in_reading_order():
    names = ["INV-10", "inv-9", "Lens 2", "lens 10"]
    assert sorted(names, key=pageopts.reading_key) == ["inv-9", "INV-10", "Lens 2", "lens 10"]


def test_filters_keep_by_words_or_a_range_read_however_typed(lib):
    items = [Item(name="A", group="Lenses", value="900"), Item(name="B", group="Grip", value="1,500")]
    lenses = pageopts.Filter("group", "Lenses")
    assert [i.name for i in items if pageopts.keeps(lib, i, lenses, None)] == ["A"]
    dear = pageopts.Filter("value", "$1,000", "")
    assert [i.name for i in items if pageopts.keeps(lib, i, dear, None)] == ["B"]
    assert all(pageopts.keeps(lib, i, pageopts.Filter("value"), None) for i in items)  # nothing typed: all kept
    assert pageopts.values([*items, Item(name="C", group="Body")], "group") == ["Body", "Grip", "Lenses"]


def test_your_last_choice_wins_over_the_profiles_default(lib):
    b = lib.pricing()
    b.page_options = {"inventory": {"paper": "a4"}}
    assert pageopts.for_page({}, b, "inventory").paper == "a4"  # a page you haven't set: the profile's
    settings: dict = {}
    pageopts.remember(settings, "inventory", pageopts.PageOptions(paper="letter", note="Mine"))
    got = pageopts.for_page(settings, b, "inventory")
    assert (got.paper, got.note) == ("letter", "Mine")


def test_the_inventory_prints_its_chosen_columns_and_gear(lib):
    o = pageopts.PageOptions(columns=["value", "gear", "company"], filters=[pageopts.Filter("value", "1000")])
    o.note = "Checked in May."
    v = document.build_inventory(lib, lib.ordered_items(), lib.pricing(), o=o)
    assert [c.title for c in v.table.cols] == ["Unit Value", "Gear", "Company"]
    assert v.table.name_col == 1 and abs(sum(c.width for c in v.table.cols) - 1) < 1e-9
    priced = [r for r in v.table.rows if r.kind in ("item", "sub")]
    assert priced and all(i.value and float(i.value.replace(",", "")) >= 1000 for i in lib.items.values()
                          if i.name in {r.cells[1] for r in priced})  # fmt: skip
    assert v.note.endswith("Checked in May.")


def test_a_page_without_the_letterhead_and_on_a4(qapp, lib):
    b = lib.pricing()
    plain = document.with_options(
        document.build_ratecard(lib, lib.ordered_items(), [], b), pageopts.PageOptions(letterhead=False)
    )
    pages = render.layout(plain, render_palette(), None, pageopts.PAPERS["a4"][1])
    words = [s.text for p in pages for s in p.steps if hasattr(s, "text")]
    assert b.name not in words and "Rate Card" in words  # the page's own title stays
    assert pages[0].size == pageopts.PAPERS["a4"][1]


def render_palette():
    from bodega.core.looks import palette

    return palette("blue", False)


def test_the_page_window_redraws_and_keeps_each_change(qapp, lib, monkeypatch):
    from bodega.ui.dialogs.preview import PageDialog
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(lib)
    drawn = []
    seen = {}

    def run(d):
        o = d.panel.options
        seen["kind"] = o.kind
        monkeypatch.setattr(w, "redraw", lambda: drawn.append(1))
        o.letterhead.setChecked(False)
        o.paper.setCurrentIndex(o.paper.findData("a4"))
        row = o.cols.item(o.cols.count() - 1)  # a column not shown at first: ticked
        row.setCheckState(row.checkState().__class__.Checked)
        o._add_filter()
        qapp.processEvents()
        seen["filters"] = len(o.opts.filters)
        o.default_wanted.emit()
        return 0

    monkeypatch.setattr(PageDialog, "exec", run)
    w.show_pages(("gear", ""), "inventory")
    kept = lib.settings["page_options"]["inventory"]
    assert seen == {"kind": "inventory", "filters": 1} and len(drawn) >= 4  # each change redrew the pages
    assert kept["letterhead"] is False and kept["paper"] == "a4" and len(kept["columns"]) == 6 and kept["filters"]
    assert lib.pricing().page_options["inventory"]["paper"] == "a4"  # and kept as the profile's default
    w.close()
