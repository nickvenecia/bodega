"""Check Out / Check In."""

from __future__ import annotations

from bodega.core import checks, document, sample
from bodega.core.model import CheckRow
from bodega.core.store import Library


def test_rows_follow_the_gear(tmp_path):
    lib = sample.fill(Library(tmp_path).load())
    r = next(iter(lib.rentals.values()))
    got = checks.rows(lib, r)
    ids = [it.id for it, _n in checks.pieces(lib, r)]
    assert [c.item_id for c in got] == ids and len(set(ids)) == len(ids)
    r.checks = [CheckRow(ids[0], out=True, note="scuff"), CheckRow("gone", note="dent")]
    again = checks.rows(lib, r)
    assert again[0].out and again[0].note == "scuff" and again[-1].item_id == "gone"  # notes are never lost
    assert checks.progress(again, back=False) == (1, len(again))


def test_check_out_and_in(qapp, data_folder, monkeypatch):
    from bodega.ui.dialogs import checklist
    from bodega.ui.window.main_window import MainWindow

    win = MainWindow(sample.fill(Library(data_folder).load()))
    win.show()
    r = next(iter(win.lib.rentals.values()))
    r.status = "booked"
    win.open("rentals", r.id)
    assert win.rentals.check.isVisibleTo(win.rentals) and win.rentals.check.text() == "Check Out…"

    def tick_all(self):
        for c in self.rows:
            c.out = c.out or not self.back
            c.back = c.back or self.back
        first = self.rows[0].item_id
        self.scan.setText(document.label_code(first))
        self._scanned()
        assert self.widgets[first].tick.isChecked()
        self.mark = True
        return checklist.CheckDialog.DialogCode.Accepted

    monkeypatch.setattr(checklist.CheckDialog, "exec", tick_all)
    win.check_rental(r.id, back=False)
    r = win.lib.rentals[r.id]
    assert r.status == "out" and r.checked_out and all(c.out for c in r.checks)
    assert Library(data_folder).load().rentals[r.id].status == "out"
    assert win.rentals.check.text() == "Check In…"
    win.check_rental(r.id, back=True)
    r = win.lib.rentals[r.id]
    assert r.status == "returned" and all(c.back for c in r.checks)
    win.close()


def test_the_plus_buttons(qapp, data_folder):
    from bodega.ui.window.main_window import MainWindow

    win = MainWindow(sample.fill(Library(data_folder).load()))
    win.show()
    win.go("gear")
    texts = [a.text() for a in win.btn_new.menu().actions()]
    assert texts == ["New Gear", "New Group…"]
    win.go("kits")
    assert win.btn_new.menu() is None
    n = len(win.lib.rentals)
    win.sidebar.btn_new_rental.click()
    assert len(win.lib.rentals) == n + 1
    assert [a.text() for a in win.sidebar.btn_new_dep.menu().actions()] == [
        "New Gear",
        "New Group…",
        "New Kit",
    ]
    win.close()


def test_only_the_hovered_sections_plus_fades_in(qapp, data_folder, monkeypatch):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QCursor

    from bodega.core import sample
    from bodega.core.store import Library
    from bodega.ui.window.main_window import MainWindow

    win = MainWindow(sample.fill(Library(data_folder).load()))
    win.show()
    sb = win.sidebar
    head = sb.heads["rental-section"]
    monkeypatch.setattr(sb, "underMouse", lambda: True)
    monkeypatch.setattr(QCursor, "pos", staticmethod(lambda: head.mapToGlobal(QPoint(4, 4))))
    sb._hover_check()
    assert sb.btn_new_rental._fade.endValue() == 1.0  # Rentals' + fades in
    assert sb.btn_new_dep.graphicsEffect().opacity() == 0.0  # Inventory's stays away
    win.close()
