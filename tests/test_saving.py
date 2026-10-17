"""Saving honestly: a write that fails is kept, said and tried again; quitting over it asks; forms with their own
Save never drop what was typed in them without asking."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QDialog

from bodega.core import sample, store
from bodega.core.model import Client, Rental
from bodega.core.store import Library
from bodega.ui.dialogs.common import Alert
from tests.ui import button, by_id, click, type_into, wait_for


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
    win.open("gear", it.id)
    type_into(win.items.name, "Edited")
    win.flush()
    assert win.banner.isVisibleTo(win) and "aren't saved" in win.banner.text.text()
    assert "no free space" in win.banner.text.text()  # the computer's real reason, in plain words
    assert "Errno" not in win.banner.text.text()
    assert win.sidebar.profile_card.sub.text() == "Not Saved"
    retry = by_id(win, "SaveRetry")
    assert retry.isActive()  # tried again every little while
    win.banner.close_btn.click()  # put away…
    win.flush()  # …it comes back while the problem lasts
    assert win.banner.isVisibleTo(win)
    full_disk.fixed()
    win.try_saving_again()
    assert not win.banner.isVisibleTo(win) and not retry.isActive()
    assert win.sidebar.profile_card.sub.text() != "Not Saved"
    assert Library(win.lib.root).load().items[it.id].name == "Edited"


def test_a_save_outside_the_autosave_is_said_too(win, full_disk, qapp):
    from PySide6.QtTest import QTest

    with pytest.raises(OSError):
        win.lib.save_client(Client(name="Lisa Kim"))
    for _ in range(100):  # said once the window's next moment comes (however slow the computer)
        if win.banner.isVisibleTo(win):
            break
        QTest.qWait(20)
    assert win.banner.isVisibleTo(win) and "renters" in win.lib.unsaved


def test_quitting_over_unsaved_changes_asks(win, full_disk, answers):
    said, asked = answers
    it = next(iter(win.lib.items.values()))
    win.open("gear", it.id)
    type_into(win.items.name, "Edited")
    said.append(QDialog.DialogCode.Rejected)  # Cancel: Bodega stays open
    assert not win.close() and win.isVisible() and asked == ["Quit Without Saving?"]
    full_disk.fixed()
    said.append(QDialog.DialogCode.Accepted)  # (not asked: the next try works)
    assert win.close()
    assert asked == ["Quit Without Saving?"]
    assert Library(win.lib.root).load().items[it.id].name == "Edited"


def test_quit_anyway_quits_over_a_save_that_keeps_failing(win, full_disk, answers):
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


def test_check_out_keeps_each_tick_as_its_made(qapp, data_folder, answers):
    """The standard's K-09: a tick, a note or a photo is kept the moment it's made, so closing (Esc, Done, the
    window's close button) never drops one, and there's nothing to ask about."""
    from bodega.ui.dialogs.checklist import CheckDialog

    _said, asked = answers
    lib = sample.fill(Library(data_folder).load())
    r = next(iter(lib.rentals.values()))
    d = CheckDialog(lib, r, back=False)
    got = []
    d.edited.connect(got.append)
    d.show()
    row = next(iter(d.widgets.values()))
    row.tick.setChecked(True)
    assert got and got[-1][0].out
    row.note.setText("Scuff on the top handle")
    row.note.textEdited.emit("Scuff on the top handle")
    assert got[-1][0].note == "Scuff on the top handle"
    d.reject()
    assert not d.isVisible() and asked == []


def test_a_tick_is_saved_before_the_check_out_window_closes(qapp, data_folder, monkeypatch):
    from bodega.ui.dialogs import checklist
    from bodega.ui.window.main_window import MainWindow

    win = MainWindow(sample.fill(Library(data_folder).load()))
    win.show()
    r = next(iter(win.lib.rentals.values()))
    r.status = "booked"
    on_disk = []

    def tick_one_and_close(self):
        next(iter(self.widgets.values())).tick.setChecked(True)
        win.flush()  # (the window's save timer, while the checklist is still open)
        on_disk.append(Library(data_folder).load().rentals[r.id].checks)
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(checklist.CheckDialog, "exec", tick_one_and_close)
    win.check_rental(r.id, back=False)
    assert on_disk and any(c.out for c in on_disk[0])
    assert win.lib.rentals[r.id].is_booked()  # kept, and not marked out
    win.close()


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

    _said, asked = answers
    second = win.lib.add_business(Business(name="Second Unit")) or next(
        b for b in win.lib.businesses.values() if b.name == "Second Unit"
    )
    from bodega.core.history import History

    win.history = History(win.lib)  # a profile you've had a while (adding then deleting it undoes itself)
    s = SettingsDialog(win.lib, win, "profiles", profile=second.id)
    s.show()
    button(s.profile_editor, "Delete Profile").click()
    assert asked == []  # the owner's call (the standard's 4.19): deleted at once, nothing asked…
    assert second.id not in win.lib.businesses
    t = s.toaster
    assert t.text == "Deleted Second Unit." and t.action_word == "Undo"  # …said with Undo, in Settings
    click(t, t.action_place.center())
    wait_for(lambda: second.id in win.lib.businesses)  # and Undo brings it back (once the click is over)
    s.close()


def test_account_settings_wait_for_an_account_service(win):
    from bodega.ui.dialogs.settings import SettingsDialog

    s = SettingsDialog(win.lib, win, "account")
    assert s.rows["account"].isHidden() and s.current_pane() == "general"  # nothing to sign in to yet
    s.close()


def test_a_new_day_refreshes_what_today_decides(win, monkeypatch, qapp):
    from datetime import timedelta

    from PySide6.QtCore import Qt

    from bodega.core import dates

    def back() -> None:  # back to Bodega (a computer asleep over midnight misses the timer)
        qapp.applicationStateChanged.emit(Qt.ApplicationState.ApplicationActive)

    tomorrow = dates.today() + timedelta(days=1)
    refreshed = []
    monkeypatch.setattr(win, "refresh", lambda: refreshed.append(1))
    back()
    assert not refreshed  # the same day: nothing to do
    monkeypatch.setattr(dates, "today", lambda: tomorrow)
    back()
    assert refreshed and by_id(win, "Midnight").isActive()  # a new day: what today decides, and midnight's next
    refreshed.clear()
    back()
    assert not refreshed  # it goes by tomorrow now: the same day again


def test_typing_without_a_pause_is_still_saved(win, qapp):
    from PySide6.QtCore import Qt

    it = next(iter(win.lib.items.values()))
    win.open("gear", it.id)
    cap = by_id(win, "SaveCap")
    type_into(win.items.name, "Typed Without a Pause")
    assert cap.isActive()  # however long the typing goes on, it's saved by then
    qapp.applicationStateChanged.emit(Qt.ApplicationState.ApplicationInactive)  # going to another app saves at once
    assert not cap.isActive()
    assert Library(win.lib.root).load().items[it.id].name == "Typed Without a Pause"


def test_quitting_while_a_job_runs_asks_first(win, answers, monkeypatch):
    said, asked = answers
    monkeypatch.setattr(win.assistant, "running", lambda: True)
    assert not win.may_quit() and asked == ["Stop and Quit?"]  # Cancel: Bodega stays open
    said.append(QDialog.DialogCode.Accepted)
    assert win.may_quit()


def test_many_rentals_written_side_by_side_keep_each_failure(data_folder, monkeypatch):
    """A delete, a renter edit or an undo saves many rentals at once, their files written side by side (a slow disk
    took seconds one after another): one that fails is kept unsaved and said, every other is still written."""
    lib = sample.fill(Library(data_folder).load())
    rentals = [Rental() for _ in range(5)]
    stuck = rentals[1].id
    real = store.write_json

    def write(path, data):
        if path.stem == stuck:
            raise OSError(28, "No space left on device")
        real(path, data)

    monkeypatch.setattr(store, "write_json", write)
    told = []
    lib.on_unsaved = lambda: told.append(1)
    for r in rentals:
        r.note = "Written side by side"
    with pytest.raises(OSError):
        lib.save_rentals(rentals)
    assert lib.unsaved == {stuck} and told and lib.why_unsaved
    again = Library(data_folder).load()
    assert all(again.rentals[r.id].note == "Written side by side" for r in rentals if r.id != stuck)
    monkeypatch.setattr(store, "write_json", real)
    assert lib.save_again() and Library(data_folder).load().rentals[stuck].note == "Written side by side"
