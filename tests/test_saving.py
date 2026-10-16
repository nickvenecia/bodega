"""Saving honestly: a write that fails is kept, said and tried again; quitting over it asks; forms with their own
Save never drop what was typed in them without asking."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QDialog

from bodega.core import sample, store
from bodega.core.model import Client
from bodega.core.store import Library
from bodega.ui.dialogs.common import Alert


@pytest.fixture
def full_disk(monkeypatch):
    """Every write fails, as on a full disk, until `.fixed()`."""

    class Disk:
        full = True

        def fixed(self):
            self.full = False

    disk = Disk()
    real = store.write_json

    def write(path, data):
        if disk.full:
            raise OSError(28, "No space left on device")
        real(path, data)

    monkeypatch.setattr(store, "write_json", write)
    return disk


@pytest.fixture
def win(qapp, data_folder):
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(sample.fill(Library(data_folder).load()))
    w.show()
    yield w
    w.lib.unsaved.clear()  # nothing left to ask about as the test's window closes
    w.close()


@pytest.fixture
def answers(monkeypatch):
    """Alerts answer from this list, in order (what a person would click); each one asked is noted."""
    said: list[str] = []
    asked: list[str] = []

    def exec_(self) -> int:
        asked.append(self.windowTitle())
        return said.pop(0) if said else QDialog.DialogCode.Rejected

    monkeypatch.setattr(Alert, "exec", exec_)
    return said, asked


def test_a_write_that_fails_is_kept_and_tried_again(data_folder, full_disk):
    full_disk.fixed()
    lib = sample.fill(Library(data_folder).load())
    full_disk.full = True
    told = []
    lib.on_unsaved = lambda: told.append(1)
    it = next(iter(lib.items.values()))
    it.name = "Renamed While the Disk Was Full"
    with pytest.raises(OSError):
        lib.save_items()
    assert lib.unsaved == {"gear"} and told
    assert not lib.save_again()
    full_disk.fixed()
    assert lib.save_again() and not lib.unsaved
    assert Library(data_folder).load().items[it.id].name == "Renamed While the Disk Was Full"


def test_a_failed_save_stays_said_until_it_works(win, full_disk):
    it = next(iter(win.lib.items.values()))
    it.name = "Edited"
    win._item_edited(it)
    win.flush()
    assert win.banner.isVisibleTo(win) and "aren't saved" in win.banner.text.text()
    assert "no free space" in win.banner.text.text()  # the computer's real reason, in plain words
    assert "Errno" not in win.banner.text.text()
    assert win.sidebar.profile_card.sub.text() == "Not Saved"
    assert win._retry_timer.isActive()
    win.banner.close_btn.click()  # put away…
    win.flush()  # …it comes back while the problem lasts
    assert win.banner.isVisibleTo(win)
    full_disk.fixed()
    win.try_saving_again()
    assert not win.banner.isVisibleTo(win) and not win._retry_timer.isActive()
    assert win.sidebar.profile_card.sub.text() != "Not Saved"
    assert Library(win.lib.root).load().items[it.id].name == "Edited"


def test_a_save_outside_the_autosave_is_said_too(win, full_disk, qapp):
    from PySide6.QtTest import QTest

    with pytest.raises(OSError):
        win.lib.save_client(Client(name="Lisa Kim"))
    QTest.qWait(20)
    assert win.banner.isVisibleTo(win) and "renters" in win.lib.unsaved


def test_quitting_over_unsaved_changes_asks(win, full_disk, answers):
    said, asked = answers
    it = next(iter(win.lib.items.values()))
    it.name = "Edited"
    win._item_edited(it)
    said.append(QDialog.DialogCode.Rejected)  # Cancel: Bodega stays open
    assert not win.close() and win.isVisible() and asked == ["Quit Without Saving?"]
    full_disk.fixed()
    said.append(QDialog.DialogCode.Accepted)  # (not asked: the next try works)
    assert win.close()
    assert asked == ["Quit Without Saving?"]
    assert Library(win.lib.root).load().items[it.id].name == "Edited"


def test_quit_anyway_quits(win, full_disk, answers):
    said, asked = answers
    win.lib.unsaved.add("gear")
    said.append(QDialog.DialogCode.Accepted)  # Try Again: still full, asked again
    said.append(Alert.OTHER)  # Quit Anyway
    assert win.close() and asked == ["Quit Without Saving?"] * 2


def test_a_renter_form_asks_before_dropping_typing(qapp, answers):
    from bodega.ui.dialogs.client import ClientDialog

    said, asked = answers
    d = ClientDialog(Client(name="Lisa Kim"), True)
    assert not d.save.isEnabled()  # nothing changed yet
    d.reject()
    assert d.result() == QDialog.DialogCode.Rejected and not asked  # nothing typed: it just closes
    d = ClientDialog(Client(name="Lisa Kim"), True)
    d.show()
    d.email.setText("lisa@example.com")
    assert d.save.isEnabled()
    said.append(QDialog.DialogCode.Rejected)  # Keep Editing
    d.reject()
    assert d.isVisible() and asked == ["Discard Your Changes?"]
    d.email.setText("")  # typed back: no change
    d.reject()
    assert not d.isVisible() and asked == ["Discard Your Changes?"]


def test_check_out_asks_before_dropping_ticks(qapp, data_folder, answers):
    from bodega.ui.dialogs.checklist import CheckDialog

    said, asked = answers
    lib = sample.fill(Library(data_folder).load())
    r = next(iter(lib.rentals.values()))
    d = CheckDialog(lib, r, back=False)
    d.show()
    next(iter(d.widgets.values())).tick.setChecked(True)
    d.reject()
    assert d.isVisible() and asked == ["Discard Your Changes?"]
    said.append(QDialog.DialogCode.Accepted)  # Discard Changes
    d.reject()
    assert not d.isVisible()


def test_settings_asks_before_another_profile_replaces_typing(win, answers):
    from bodega.core.model import Business
    from bodega.ui.dialogs.settings import SettingsDialog

    said, asked = answers
    win.lib.add_business(Business(name="Second Unit"))
    s = SettingsDialog(win.lib, win, "profiles")
    s.show()
    editor = s.profile_editor
    editor.tagline.setText("Typed and not saved")
    other = next(i for i in range(s.profile_pick.count()) if s.profile_pick.itemText(i) == "Second Unit")
    s.profile_pick.setCurrentIndex(other)
    s.profile_pick.activated.emit(other)  # Keep Editing
    assert s.profile_editor is editor and asked == ["Discard Your Changes?"]
    assert s.profile_pick.currentText() != "Second Unit"
    s.reject()  # closing Settings asks too (Keep Editing again)
    assert s.isVisible() and len(asked) == 2
    said.append(QDialog.DialogCode.Accepted)
    s.reject()
    assert not s.isVisible()


def test_discarding_is_never_what_return_does(qapp):
    from bodega.ui.dialogs.common import Alert

    a = Alert(None, "Discard Your Changes?", "", "Discard Changes", "Keep Editing", danger=True, safe=True)
    assert a.go.text() == "Keep Editing" and a.go.isDefault()


def test_deleting_a_profile_names_it_and_undo_brings_it_back(win, answers):
    from bodega.core.model import Business
    from bodega.ui.dialogs.settings import SettingsDialog

    said, asked = answers
    second = win.lib.add_business(Business(name="Second Unit")) or next(
        b for b in win.lib.businesses.values() if b.name == "Second Unit"
    )
    from bodega.core.history import History

    win.history = History(win.lib)  # a profile you've had a while (adding then deleting it undoes itself)
    s = SettingsDialog(win.lib, win, "profiles", profile=second.id)
    said.append(QDialog.DialogCode.Accepted)
    s.profile_editor._delete()
    assert asked == ["Delete Second Unit?"]
    assert second.id not in win.lib.businesses
    s.close()
    win.undo()
    assert second.id in win.lib.businesses  # the alert's "Edit › Undo brings it back" holds


def test_account_settings_wait_for_an_account_service(win):
    from bodega.ui.dialogs.settings import SettingsDialog

    s = SettingsDialog(win.lib, win, "account")
    assert s.rows["account"].isHidden() and s.current_pane() == "general"  # nothing to sign in to yet
    s.close()


def test_a_new_day_refreshes_what_today_decides(win, monkeypatch):
    from datetime import timedelta

    from bodega.core import dates

    tomorrow = dates.today() + timedelta(days=1)
    refreshed = []
    monkeypatch.setattr(win, "refresh", lambda: refreshed.append(1))
    win._new_day()
    assert not refreshed  # the same day: nothing to do
    monkeypatch.setattr(dates, "today", lambda: tomorrow)
    win._new_day()
    assert refreshed and win._day == tomorrow and win._midnight.isActive()


def test_typing_without_a_pause_is_still_saved(win):
    from PySide6.QtCore import Qt

    it = next(iter(win.lib.items.values()))
    it.name = "Typed Without a Pause"
    win._item_edited(it)
    assert win._save_cap.isActive()  # however long the typing goes on, it's saved by then
    win._app_state(Qt.ApplicationState.ApplicationInactive)  # going to another app saves at once
    assert not win._save_cap.isActive()
    assert Library(win.lib.root).load().items[it.id].name == "Typed Without a Pause"


def test_quitting_while_a_job_runs_asks_first(win, answers, monkeypatch):
    said, asked = answers
    monkeypatch.setattr(win.assistant, "running", lambda: True)
    assert not win.may_quit() and asked == ["Stop and Quit?"]  # Cancel: Bodega stays open
    said.append(QDialog.DialogCode.Accepted)
    assert win.may_quit()
