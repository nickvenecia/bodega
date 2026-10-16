"""Accessibility (the standard's Part 7 and G.1): the system's Reduce Motion, Increase Contrast and Reduce
Transparency; names for screen readers; and the keyboard: Esc one layer at a time, Tab through the places,
the neighbouring row after a delete."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit

from bodega.core import sample
from bodega.core.store import Library
from bodega.ui.style import tokens


@pytest.fixture
def win(qapp, data_folder):
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(sample.fill(Library(data_folder).load()))
    w._restored = True
    w.resize(1440, 900)
    w.show()
    yield w
    w.close()


def test_increase_contrast_and_reduce_transparency_change_the_look():
    try:
        for scheme in ("light", "dark"):
            look = tokens.LIGHT if scheme == "light" else tokens.DARK
            tokens.use(scheme, "", contrast=True, opaque=True)
            assert tokens.contrast(tokens.MUTED, look["BG"]) >= 7  # secondary words at 7:1
            assert look["BORDER_STRONG"] == tokens.BORDER and look["MUTED"] == tokens.FAINT
            assert tokens.GLASS.startswith("#")  # solid glass
    finally:
        tokens.use("dark", "")
    assert tokens.GLASS.startswith("rgba(")


def test_reduce_motion_opens_the_panel_at_once(win, monkeypatch):
    monkeypatch.setenv("BODEGA_REDUCE_MOTION", "1")
    win.open("gear", next(iter(win.lib.items)))
    assert win.dock.opened and win.dock._t == 1.0  # no slide: it's simply there


def test_esc_closes_one_layer_at_a_time(win):
    win.open("gear", next(iter(win.lib.items)))
    win.activateWindow()
    QTest.qWaitForWindowActive(win)
    win.search.setFocus()
    win.search.setText("sony")
    win.escape()
    assert win.search.text() == "" and win.dock.opened  # first the words
    win.escape()
    assert not win.search.hasFocus() and win.dock.opened  # then the search itself
    win.escape()
    assert not win.dock.opened or win.items.it is None  # then the panel


def test_fields_are_known_by_their_labels(win):
    win.open("gear", next(iter(win.lib.items)))
    QApplication.processEvents()
    named = {f.accessibleName() for f in win.items.findChildren(QLineEdit) if f.isVisible()}
    assert {"Company", "Series"} <= named


def test_tab_reaches_the_places_and_return_opens_one(win):
    from bodega.ui.components.panels import NavRow

    rows = [r for r in win.sidebar.findChildren(NavRow) if r.isVisible()]
    assert all(r.focusPolicy() & Qt.FocusPolicy.TabFocus for r in rows)
    kits = win.sidebar.rows["kits"]
    kits.setFocus()
    QTest.keyClick(kits, Qt.Key.Key_Return)
    QTest.qWait(20)
    assert win.view_key == "kits"


def test_after_a_delete_from_the_keyboard_the_next_row_is_current(win, monkeypatch):
    from bodega.ui.window import editing
    from bodega.ui.window.tables import ID

    monkeypatch.setattr(editing, "confirm", lambda *a, **k: True)
    t = win.gear_table
    rows = [r.data(0, ID) for r in t.showing_rows()]
    victim = next(i for n, i in enumerate(rows[:-1]) if not win.lib.rentals_with(i) and not win.lib.items[i].parent
                  and not any(k.parent == i for k in win.lib.items.values()))  # fmt: skip
    after = rows[rows.index(victim) + 1]
    win.activateWindow()
    QTest.qWaitForWindowActive(win)
    t.setFocus()
    win.delete_gear([victim])
    cur = t.currentItem()
    assert cur is not None and cur.data(0, ID) == after


def test_settings_starts_with_the_keyboard_on_its_section(win):
    from bodega.ui.dialogs.settings import SettingsDialog

    s = SettingsDialog(win.lib, win, "profiles")
    s.show()
    s.activateWindow()
    QTest.qWaitForWindowActive(s)
    assert QApplication.focusWidget() is s.rows["profiles"]
    s.close()


def test_a_toast_is_said_aloud(win):
    win.toast("Saved.", "done")
    assert win.toaster.accessibleName() == "Saved."


def test_a_folded_card_says_so(win):
    from bodega.ui.components.widgets import Disclosure

    d = Disclosure("Agreement")
    assert d.header.accessibleName() == "Agreement" and d.header.accessibleDescription() == "Collapsed"
    d.set_open(True)
    assert d.header.accessibleDescription() == "Expanded"


def test_screen_readers_hear_dates_lines_the_card_and_the_accent(win):
    from bodega.ui.components.widgets import AccentPicker
    from bodega.ui.style import tokens

    r = next(iter(win.lib.rentals.values()))
    win.open("rentals", r.id)
    assert win.rentals.pickup.accessibleName() == "Pickup" and win.rentals.ret.accessibleName() == "Return"
    card = win.sidebar.profile_card
    assert "Profiles and Settings" in card.accessibleName()
    picker = AccentPicker("purple")
    assert picker.accessibleName() == "Accent Color"
    assert picker.accessibleDescription() == tokens.ACCENTS["purple"][0]
    picker.deleteLater()


def test_a_status_line_is_heard_as_it_changes(qapp, monkeypatch):
    from bodega.ui.components import widgets

    heard = []
    monkeypatch.setattr(widgets, "announce", lambda _w, text: heard.append(text))
    line = widgets.status_line()
    line.show()
    line.setText("Checking…")
    line.setText("Checking…")  # the same words again: said once
    line.setText("$5,998 at B&H")
    assert heard == ["Checking…", "$5,998 at B&H"]
    line.deleteLater()


def test_home_and_end_go_to_a_menus_first_and_last_choice(qapp):
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication, QMenu

    m = QMenu()  # (the qapp fixture set Bodega's app up, with its event filter)
    for name in ("Apple", "Banana", "Cherry"):
        m.addAction(name)
    m.addSeparator()
    QApplication.sendEvent(m, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_End, Qt.KeyboardModifier.NoModifier))
    assert m.activeAction().text() == "Cherry"
    QApplication.sendEvent(
        m, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Home, Qt.KeyboardModifier.NoModifier)
    )
    assert m.activeAction().text() == "Apple"
    m.deleteLater()


def test_clickable_rows_work_from_the_keyboard(win):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    head = next(iter(win.sidebar.heads.values()))
    assert head.focusPolicy() == Qt.FocusPolicy.TabFocus and head.accessibleName()
    was = head.folded
    QTest.keyClick(head, Qt.Key.Key_Space)
    QApplication.processEvents()  # (it acts once the key is over)
    assert head.folded != was and head.accessibleDescription() in ("Collapsed", "Expanded")
    from PySide6.QtWidgets import QFrame

    r = next(iter(win.lib.rentals.values()))
    win.open("rentals", r.id)
    heads = [w for w in win.rentals.findChildren(QFrame) if w.objectName() == "LineHead"]
    assert heads and all(h.focusPolicy() == Qt.FocusPolicy.TabFocus for h in heads)  # each line's head


def test_every_page_names_what_the_keyboard_can_reach(win):
    """On every place, in light and dark, with something open: each control you can Tab to has a name."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QAbstractButton,
        QAbstractSpinBox,
        QApplication,
        QComboBox,
        QLineEdit,
        QWidget,
    )

    from bodega.app import set_appearance
    from bodega.ui.window.common import PLACES

    def unnamed() -> list[str]:
        out = []
        for w in win.findChildren(QWidget):
            if not w.isVisible() or w.focusPolicy() == Qt.FocusPolicy.NoFocus:
                continue
            if isinstance(w.parent(), QAbstractSpinBox | QComboBox):
                continue  # Qt's own inner part of a box that's named itself
            named = w.accessibleName().strip()
            if isinstance(w, QAbstractButton):
                named = named or w.text().strip()
            elif isinstance(w, QLineEdit | QComboBox | QAbstractSpinBox):
                named = named or (w.placeholderText().strip() if isinstance(w, QLineEdit) else "")
            else:
                continue  # rows and lists say themselves (their names are tested where they're made)
            if not named:
                out.append(f"{type(w).__name__} {w.objectName()!r} {w.toolTip()!r}")
        return out

    qapp = QApplication.instance()
    try:
        for look in ("light", "dark"):
            set_appearance(qapp, look)
            for p in PLACES:
                win.go(p.key)
                QApplication.processEvents()
                assert not unnamed(), (look, p.key, unnamed())
            for kind, where in (
                ("gear", win.lib.items),
                ("packages", win.lib.packages),
                ("rentals", win.lib.rentals),
            ):
                win.open(kind, next(iter(where)))
                QApplication.processEvents()
                assert not unnamed(), (look, kind, unnamed())
    finally:
        set_appearance(qapp, "dark", "")
