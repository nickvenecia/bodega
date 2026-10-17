"""Dialogs as sheets (the standard's 4.9, G.18 and C-26): over the window, never a window of their own; the window
behind blurred and dimmed; a ✕ circle level with the title; Esc and the ✕ close; a click on the dimmed area closes
what wouldn't lose work, and never reaches what's underneath; focus goes in and comes back."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLabel

from bodega.core import sample
from bodega.core.store import Library
from bodega.ui.components import sheet
from bodega.ui.style import tokens

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def win(qapp, data_folder, monkeypatch):
    from bodega.ui.window.main_window import MainWindow

    monkeypatch.setenv("BODEGA_REDUCE_MOTION", "1")
    w = MainWindow(sample.fill(Library(data_folder).load()))
    w.resize(1100, 760)
    w.show()
    QTest.qWait(50)
    yield w
    w.close()


def renter(win):
    from bodega.ui.dialogs.client import ClientDialog

    r = next(iter(win.lib.rentals.values()))
    d = ClientDialog(r.client, False, win)
    d.show()
    QTest.qWait(20)
    return d


def the_sheet(d) -> sheet.Sheet:
    return next(c for c in d.children() if isinstance(c, sheet.Sheet))


def test_a_dialog_shows_over_its_window_on_a_panel(win):
    d = renter(win)
    s = the_sheet(d)
    assert d.property("sheet") and d.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert d.geometry().size() == win.size() and d.mapToGlobal(QPoint(0, 0)) == win.mapToGlobal(QPoint(0, 0))
    p = s.panel
    assert abs(p.center().x() - d.width() // 2) <= 1 and abs(p.center().y() - d.height() // 2) <= 1  # the middle
    assert p.width() >= tokens.DIALOG_W_WIDE and s.radius == tokens.RADIUS_XL
    assert s.picture is not None and s.picture.size() == win.size()  # the window, as it was, behind it
    fields = [w for w in d.findChildren(QLabel) if w.isVisible() and w.parent() is not s.backdrop]
    assert all(p.contains(w.geometry().translated(w.parentWidget().mapTo(d, QPoint(0, 0)))) for w in fields)
    d.reject()


def test_its_close_circle_sits_level_with_the_title_and_closes_it(win):
    d = renter(win)
    s = the_sheet(d)
    b = s.close_btn
    assert b.isVisible() and b.accessibleName() == "Close" and b.width() == tokens.CONTROL_H
    title = next(t for t in d.findChildren(QLabel) if t.objectName() == "DialogTitle")
    assert abs(b.geometry().center().y() - title.mapTo(d, QPoint(0, title.height() // 2)).y()) <= 1
    assert b.geometry().right() + 1 == s.panel.right() + 1 - tokens.SHEET_CLOSE_INSET
    QTest.mouseClick(b, Qt.MouseButton.LeftButton)
    assert not d.isVisible() and d.result() == QDialog.DialogCode.Rejected


def test_esc_closes_it(win):
    d = renter(win)
    QTest.keyClick(d, Qt.Key.Key_Escape)
    assert not d.isVisible()


def test_a_click_outside_closes_it_unless_that_would_lose_work(win, monkeypatch):
    from bodega.ui.dialogs import common

    d = renter(win)
    s = the_sheet(d)
    outside = QPoint(s.panel.left() // 2, s.panel.top() // 2)
    QTest.mouseClick(s.backdrop, Qt.MouseButton.LeftButton, pos=outside)
    assert not d.isVisible()  # nothing typed: it just closes
    d = renter(win)
    s = the_sheet(d)
    d.name.setText("Someone Else")  # typed: closing asks first (it's a form with its own Save)
    asked = []
    monkeypatch.setattr(common, "ask_discard", lambda parent: asked.append(1) or False)
    QTest.mouseClick(s.backdrop, Qt.MouseButton.LeftButton, pos=outside)
    assert asked and d.isVisible()
    inside = s.panel.center()
    QTest.mouseClick(s.backdrop, Qt.MouseButton.LeftButton, pos=inside)  # (on the panel: nothing)
    assert d.isVisible()
    monkeypatch.setattr(common, "ask_discard", lambda parent: True)
    d.reject()


def test_an_alert_has_no_close_circle_sits_high_and_isnt_closed_from_outside(win):
    from bodega.ui.dialogs.common import Alert

    a = Alert(win, "Delete Sony FX6?", "It isn't on any rental.", "Delete", "Cancel", danger=True)
    a.show()
    QTest.qWait(20)
    s = the_sheet(a)
    assert s.close_btn is None and not s.panel_drawn  # (its card is its own; Cancel is its way out)
    assert s.panel.center().y() < a.height() // 2  # a little above the middle
    QTest.mouseClick(s.backdrop, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
    assert a.isVisible()  # a decision isn't dropped by a stray click
    QTest.keyClick(a, Qt.Key.Key_Escape)
    assert not a.isVisible() and a.result() == QDialog.DialogCode.Rejected


def test_over_another_sheet_the_window_is_dimmed_not_blurred_twice(win, monkeypatch):
    from bodega.ui.dialogs.common import Alert

    blurs = []
    real = sheet.still
    monkeypatch.setattr(sheet, "still", lambda w, blur: blurs.append(blur) or real(w, blur))
    d = renter(win)
    a = Alert(d, "Discard Your Changes?", "", "Discard Changes", "Keep Editing")
    a.show()
    QTest.qWait(20)
    assert blurs == [tokens.SHEET_BLUR, 0]
    a.reject()
    d.reject()


def test_settings_is_the_window_over_the_app(win):
    from bodega.ui.dialogs.settings import SettingsDialog

    d = SettingsDialog(win.lib, win)
    d.show()
    QTest.qWait(20)
    s = the_sheet(d)
    assert s.kind == "window" and s.radius == tokens.GLASS_R
    assert s.panel.left() >= tokens.WINDOW_PAD and s.panel.top() >= tokens.WINDOW_PAD
    d.show_pane("profiles")
    QTest.qWait(20)
    form = d.panes["profiles"].findChildren(QDialog)
    assert form and not any(f.isWindow() for f in form)  # a form sitting in Settings isn't a sheet of its own
    d.reject()


def test_it_comes_in_unless_motion_is_reduced(win, monkeypatch):
    monkeypatch.setenv("BODEGA_REDUCE_MOTION", "0")
    d = renter(win)
    s = the_sheet(d)
    assert s.lift > 0 and d.windowOpacity() < 1  # fading in, rising
    QTest.qWait(tokens.SHEET_RISE_MS + 150)
    assert d.windowOpacity() == pytest.approx(1.0) and s.lift == 0
    d.reject()
    monkeypatch.setenv("BODEGA_REDUCE_MOTION", "1")
    d = renter(win)
    assert d.windowOpacity() == 1.0 and the_sheet(d).lift == 0  # simply there
    d.reject()


def test_the_panel_grows_with_what_it_holds(win):
    d = renter(win)
    s = the_sheet(d)
    before = s.panel.height()
    for _ in range(4):
        d.layout().addWidget(QLabel("One more line of words that came along later"))
    QApplication.processEvents()
    assert s.panel.height() > before
    d.reject()


def test_on_wayland_a_dialog_stays_a_window(win, monkeypatch):
    from bodega.ui.dialogs.client import ClientDialog

    monkeypatch.setattr(QGuiApplication, "platformName", staticmethod(lambda: "wayland"))
    r = next(iter(win.lib.rentals.values()))
    d = ClientDialog(r.client, False, win)
    assert not d.property("sheet") and not any(isinstance(c, sheet.Sheet) for c in d.children())
    d.deleteLater()


def test_every_dialog_is_a_sheet_or_says_why_not():
    """Every dialog Bodega makes calls sheet.prepare() as it's made, or says SHEET = False (and why)."""
    missing = []
    for path in sorted((ROOT / "bodega" / "ui").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                (isinstance(b, ast.Name) and b.id == "QDialog") for b in node.bases
            ):
                body = ast.get_source_segment(text, node) or ""
                if "sheet.prepare(self)" not in body and "SHEET = False" not in body:
                    missing.append(f"{path.name}: {node.name}")
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                f = node.value.func
                if isinstance(f, ast.Name) and f.id == "QDialog":
                    name = node.targets[0].id if isinstance(node.targets[0], ast.Name) else "?"
                    if f"sheet.prepare({name})" not in text:
                        missing.append(f"{path.name}: {name} = QDialog(…)")
    assert not missing, missing


def test_with_its_window_not_showing_it_is_the_panel_alone(win):
    win.hide()
    d = renter(win)
    s = the_sheet(d)
    assert s.alone and s.picture is None and s.panel == d.rect()  # no scrim: just the form, mid-screen
    assert d.width() >= tokens.DIALOG_W_WIDE and d.height() < 2000
    d.reject()
    win.show()


def test_it_follows_its_window(win):
    d = renter(win)
    win.move(win.pos() + QPoint(40, 30))
    QApplication.processEvents()
    assert d.mapToGlobal(QPoint(0, 0)) == win.mapToGlobal(QPoint(0, 0))
    d.reject()


def test_focus_goes_in_and_comes_back(win):
    t = win.gear_table
    win.activateWindow()
    t.setFocus()
    QApplication.processEvents()
    assert QApplication.focusWidget() is t
    d = renter(win)
    d.activateWindow()
    QApplication.processEvents()
    f = QApplication.focusWidget()
    assert f is not None and d.isAncestorOf(f)  # in the sheet (its first field)
    d.reject()
    QApplication.processEvents()
    assert QApplication.focusWidget() is t  # back where it was
