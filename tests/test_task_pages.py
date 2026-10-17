"""Import and Review are pages (the standard's 4.9 and C-25: anything that would make a dialog wider than about 640 is
a page): each takes the place of the page beside the sidebar, on the window's own background, with no scrim, panel
or ✕, its title, Cancel and its main action across its top as a page's are. The sidebar stays where it was."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel

from bodega.core import importer, sample
from bodega.core.store import Library
from bodega.services.ai import tasks
from bodega.ui.components import sheet
from bodega.ui.style import tokens
from tests.ui import keep_size


@pytest.fixture
def win(qapp, data_folder, monkeypatch):
    from bodega.ui.window.main_window import MainWindow

    monkeypatch.setenv("BODEGA_REDUCE_MOTION", "1")
    w = MainWindow(sample.fill(Library(data_folder).load()))
    keep_size(w)
    w.resize(*tokens.WINDOW_MIN)
    w.show()
    QTest.qWait(50)
    yield w
    w.close()


def _sheet(d) -> sheet.Sheet:
    return next(c for c in d.children() if isinstance(c, sheet.Sheet))


def _on_screen(w, r: QRect) -> QRect:
    return QRect(w.mapToGlobal(r.topLeft()), r.size())


def _import_page(win, tmp_path):
    from bodega.ui.dialogs.import_sheet import ImportDialog

    path = tmp_path / "Gear List.csv"
    importer.write_csv(list(win.lib.items.values()), win.lib.items, path)
    return ImportDialog(path, importer.load_rows(path), set(), win)


def test_import_takes_the_place_of_the_page_beside_the_sidebar(win, tmp_path):
    d = _import_page(win, tmp_path)
    d.show()
    QTest.qWait(20)
    s = _sheet(d)
    assert s.kind == "page" and s.close_btn is None and s.picture is None  # no ✕, nothing blurred behind it
    assert d.geometry() == _on_screen(win, win.page_area())
    side = win.sidebar.mapToGlobal(QPoint(win.sidebar.width(), 0)).x()
    assert d.geometry().left() >= side  # the sidebar still shows beside it
    title = next(t for t in d.findChildren(QLabel) if t.objectName() == "PageTitle")
    assert title.text() == "Import Gear List.csv"
    bar = title.parentWidget()
    assert bar.objectName() == "Toolbar" and bar.height() == tokens.TOOLBAR_H  # its top, as a page's is
    assert d.go.parentWidget() is bar and d.go.text().startswith("Import ")
    assert not d.go.hasFocus()  # (the page's own rows take the focus first, not its buttons)
    QTest.keyClick(d, Qt.Key.Key_Escape)  # Esc is Cancel
    assert not d.isVisible() and d.result() == 0


def test_a_page_follows_the_window_and_the_panel_beside_it(win, tmp_path):
    it = next(iter(win.lib.items.values()))
    win.open("gear", it.id)  # the panel on the right open: the page covers it too
    QTest.qWait(400)
    d = _import_page(win, tmp_path)
    d.show()
    QTest.qWait(20)
    assert d.geometry().right() >= win.dock.mapToGlobal(QPoint(win.dock.width() - 1, 0)).x()
    win.resize(win.width() + 120, win.height())
    QTest.qWait(20)
    assert d.geometry() == _on_screen(win, win.page_area())
    d.reject()


def test_review_is_a_page_and_ticks_by_row(win):
    from bodega.ui.dialogs.ai_review import ReviewDialog

    a, b = list(win.lib.items.values())[:2]
    changes = [tasks.Change(a.id, "name", a.name, a.name + " Kit", "bhphotovideo.com"),
               tasks.Change(b.id, "group", b.group, "Grip", tasks.AI_SAID, unsure=True)]  # fmt: skip
    d = ReviewDialog("Tidy Names", tasks.Result(changes, []), {a.id: a.name, b.id: b.name}, win)
    d.show()
    QTest.qWait(20)
    assert _sheet(d).kind == "page" and d.geometry() == _on_screen(win, win.page_area())
    (row_a, _), (row_b, _) = d.rows
    assert row_a.text(1) == a.name and d.go.text() == "Apply 1 Change"  # the guess is left unticked
    rect = d.list.visualItemRect(row_b)
    QTest.mouseClick(d.list.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())  # a click ticks the row
    assert row_b.isSelected() and d.go.text() == "Apply 2 Changes" and d.chosen() == changes
    d.reject()
