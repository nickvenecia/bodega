"""Single keys (the standard's 6.1): N, E, D, /, ? and A work alone, outside text fields, with nothing open over the
window, never with ⌘, Ctrl or ⌥ held; Settings › Keyboard Shortcuts turns them off."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from bodega.core import sample
from bodega.core.store import Library
from tests.ui import press

SHIFT, CTRL, ALT = (
    Qt.KeyboardModifier.ShiftModifier,
    Qt.KeyboardModifier.ControlModifier,
    Qt.KeyboardModifier.AltModifier,
)


@pytest.fixture
def win(qapp, data_folder):
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(sample.fill(Library(data_folder).load()))
    w.show()
    w.activateWindow()
    QTest.qWaitForWindowActive(w)  # (a shortcut works in the window you're in)
    yield w
    w.close()


def on_the_list(win):
    win.go("gear")
    t = win.gear_table
    t.setFocus()
    return t


def test_n_makes_this_pages_new_thing_and_types_in_a_field(win):
    t = on_the_list(win)
    before = len(win.lib.items)
    QTest.keyClick(t, Qt.Key.Key_N)
    assert len(win.lib.items) == before + 1 and win.items.name.hasFocus()  # a new piece, its name ready
    QTest.keyClicks(win.items.name, "N")  # in a text field a letter is a letter
    assert win.items.name.text() == "N" and len(win.lib.items) == before + 1
    win.go("kits")
    win.kit_table.setFocus()
    kits = len(win.lib.packages)
    QTest.keyClick(win.kit_table, Qt.Key.Key_N, SHIFT)  # Shift doesn't change what a letter does
    assert len(win.lib.packages) == kits + 1


def test_e_opens_whats_marked_with_the_cursor_in_its_name(win):
    t = on_the_list(win)
    win.deselect()
    QTest.keyClick(t, Qt.Key.Key_E)  # nothing marked: nothing to edit
    assert not win.dock.opened
    row = next(iter(t.showing_rows()))
    win.search.setFocus()
    press(win.search, Qt.Key.Key_Down)  # ↓ in the search marks the first row, without opening it
    assert t.currentItem() is row and not win.dock.opened
    t.setFocus()
    QTest.keyClick(t, Qt.Key.Key_E)
    assert win.dock.opened and win.items.it.id == row.data(0, 256) and win.items.name.hasFocus()


def test_d_deletes_whats_picked_with_undo_and_ctrl_d_duplicates(win):
    t = on_the_list(win)
    free = next(i for i in win.lib.items.values() if not win.lib.rentals_with(i.id) and not i.parent)
    win.open("gear", free.id)
    t.setFocus()
    n = len(win.lib.items)
    QTest.keyClick(t, Qt.Key.Key_D, CTRL)  # ⌘D is Duplicate, never Delete
    assert len(win.lib.items) == n + 1 and free.id in win.lib.items
    copy = win.items.it.id
    win.open("gear", free.id)
    assert win.gear_table.chosen_ids() == [free.id]  # only what's open is picked (never the copy too)
    t.setFocus()
    QTest.keyClick(t, Qt.Key.Key_D)
    assert free.id not in win.lib.items and copy in win.lib.items and win.toaster.action_word == "Undo"


def test_slash_goes_to_the_search_and_question_mark_to_the_shortcuts(win, monkeypatch):
    t = on_the_list(win)
    QTest.keyClick(t, Qt.Key.Key_Slash)
    assert win.search.hasFocus()
    opened = []
    monkeypatch.setattr(win, "open_settings", lambda pane="": opened.append(pane))
    t.setFocus()
    QTest.keyClick(t, Qt.Key.Key_Question, SHIFT)  # (typed with Shift on most keyboards)
    QTest.keyClick(win.search, Qt.Key.Key_Question, SHIFT)  # in the search it's a question mark
    assert opened == ["shortcuts"] and win.search.text().endswith("?")


def test_a_opens_the_assistant_and_never_closes_it(win):
    t = on_the_list(win)
    QTest.keyClick(t, Qt.Key.Key_A)
    q = win.assistant.question
    assert win.assistant_showing() and (q.hasFocus() or not q.isEnabled())  # (it waits for a provider here)
    t.setFocus()
    QTest.keyClick(t, Qt.Key.Key_A)
    assert win.assistant_showing()  # A opens; ⌘J or ✕ closes
    QTest.keyClick(t, Qt.Key.Key_A, ALT)  # never with ⌥ (or ⌘, or Ctrl) held
    assert win.assistant_showing()


def test_single_keys_can_be_turned_off_in_settings(win):
    from bodega.ui.dialogs.settings import SettingsDialog

    s = SettingsDialog(win.lib, win, "shortcuts")
    assert s.single.isChecked()  # on until you turn them off
    s.single.setChecked(False)
    s.close()
    assert Library(win.lib.root).load().settings["single_keys"] is False  # kept
    t = on_the_list(win)
    n = len(win.lib.items)
    QTest.keyClick(t, Qt.Key.Key_N)
    assert len(win.lib.items) == n  # off: a letter does nothing
    QTest.keyClick(t, Qt.Key.Key_N, CTRL)
    assert len(win.lib.items) == n + 1  # ⌘N and Ctrl shortcuts stay on


def test_the_shortcuts_list_names_every_single_key(win):
    from PySide6.QtWidgets import QLabel

    from bodega.ui.dialogs.shortcuts import ShortcutsList
    from bodega.ui.window.menus import SINGLE_KEYS

    shown = ShortcutsList(win.menuBar(), win.single_acts)
    caps = {w.text() for w in shown.findChildren(QLabel) if w.objectName() == "KeyCap"}
    assert {key for key, _what, _do in SINGLE_KEYS} <= caps
    shown.deleteLater()


def test_every_key_the_shortcuts_list_shows_reaches_its_command(win):
    """The standard's I-15: every key the menus and the single keys list is bound where it's shown, pressed for real
    on the list (each command is held back as its key reaches it, so Quit doesn't quit)."""
    from PySide6.QtCore import QEvent, QObject

    class Hold(QObject):
        reached: list = []

        def eventFilter(self, obj, e):
            if e.type() == QEvent.Type.Shortcut:
                self.reached.append(obj)
                return True
            return False

    hold = Hold()
    menus = [top.menu() for top in win.menuBar().actions() if top.menu() is not None]
    keyed = [a for m in menus for a in m.actions() if a.shortcuts() and not a.shortcuts()[0].isEmpty()]
    keyed += win.single_acts
    for a in keyed:
        a.installEventFilter(hold)
    t = on_the_list(win)
    missed = []
    for a in keyed:
        for seq in a.shortcuts():
            hold.reached.clear()
            t.setFocus()
            QTest.keyClick(t, seq[0].key(), seq[0].keyboardModifiers())
            if hold.reached != [a]:
                missed.append((a.text(), seq.toString()))
    assert not missed
    assert len(keyed) >= 20  # (a Mac moves Quit and Settings… into the Bodega menu, out of these lists)


def test_the_anywhere_keys_do_what_the_list_says(win):
    """Settings › Keyboard Shortcuts › Anywhere: Delete (Backspace) deletes what's picked, Esc closes the panel."""
    from bodega.ui.dialogs.shortcuts import EXTRA

    assert [t for t, _k in EXTRA] == ["Delete What's Picked", "Close Panel"]
    t = on_the_list(win)
    free = next(i for i in win.lib.items.values() if not win.lib.rentals_with(i.id) and not i.parent)
    win.open("gear", free.id)
    t.setFocus()
    QTest.keyClick(t, Qt.Key.Key_Backspace)
    assert free.id not in win.lib.items
    win.open("gear", next(iter(win.lib.items)))
    t.setFocus()
    QTest.keyClick(t, Qt.Key.Key_Escape)
    assert not win.dock.opened
