"""The Renters page (the standard's N-18: every kind of record has its own page and edits in place): a list of everyone
you rent to, and the one you pick on the right, its form with Cancel and Save Changes, then its rentals. Renters are
still saved only on purpose: typing asks before it's dropped, and a new renter is a sheet, kept once you save it."""

from __future__ import annotations

import pytest

from bodega.core import sample
from bodega.core.model import Client
from bodega.core.store import Library


@pytest.fixture
def win(qapp, data_folder):
    from bodega.ui.window.main_window import MainWindow

    lib = sample.fill(Library(data_folder).load())
    lib.save_client(Client(name="Sam Ortiz", email="sam@ortiz.example"))
    w = MainWindow(lib)
    w.show()
    yield w
    w.close()


def _alex(w) -> Client:
    return next(c for c in w.lib.clients.values() if c.name == "Alex Rivera")


def test_the_page_lists_every_renter_with_their_rentals(win, qapp):
    win.go("renters")
    rows = {r.text(1): r for r in win.renter_table.record_rows()}
    assert set(rows) == {"Alex Rivera", "Sam Ortiz"}
    assert rows["Alex Rivera"].text(5) == "1" and rows["Sam Ortiz"].text(5) == "0"
    assert rows["Alex Rivera"].text(2) == "Northwind Media" and rows["Alex Rivera"].text(6)  # the last rental's dates
    win.search.setText("ortiz.example")  # found by email too
    qapp.processEvents()
    assert [r.text(1) for r in win.renter_table.showing_rows()] == ["Sam Ortiz"]


def test_a_renter_edits_in_place_and_its_bookings_follow(win, qapp):
    alex = _alex(win)
    win.open("renters", alex.id)
    p = win.renters
    assert win.inspector.currentWidget() is p and p.current_id() == alex.id
    assert not p.editor.save.isEnabled()  # nothing changed yet
    assert p.editor.save.text() == "Save Changes"
    assert "Rentals · 1" in p.rentals_card.title.text()
    p.editor.phone.setText("(602) 555-0100")
    assert p.editor.save.isEnabled()
    p.editor.save.click()
    assert win.lib.clients[alex.id].phone == "(602) 555-0100"
    booked = next(r for r in win.lib.rentals.values() if r.client.id == alex.id)
    assert booked.client.phone == "(602) 555-0100"  # a booking not out the door yet follows the change
    assert p.current_id() == alex.id and not p.editor.save.isEnabled()  # still open, saved


def test_cancel_puts_back_what_is_saved(win, qapp, monkeypatch):
    from bodega.ui.dialogs import common

    alex = _alex(win)
    win.open("renters", alex.id)
    win.renters.editor.email.setText("typo@")
    monkeypatch.setattr(common, "ask_discard", lambda parent: True)
    win.renters.editor.reject()
    qapp.processEvents()
    assert win.renters.editor.email.text() == alex.email and win.lib.clients[alex.id].email == alex.email


def test_typing_not_saved_asks_before_another_renter_opens(win, qapp, monkeypatch):
    from bodega.ui.dialogs import common

    alex, sam = _alex(win), next(c for c in win.lib.clients.values() if c.name == "Sam Ortiz")
    win.open("renters", alex.id)
    win.renters.editor.phone.setText("555")
    asked = []
    monkeypatch.setattr(common, "ask_discard", lambda parent: asked.append(1) or False)  # Keep Editing
    win.open("renters", sam.id)
    assert asked and win.renters.current_id() == alex.id and win.renters.editor.phone.text() == "555"
    monkeypatch.setattr(common, "ask_discard", lambda parent: True)  # Discard Changes
    win.open("renters", sam.id)
    assert win.renters.current_id() == sam.id
    assert win.lib.clients[alex.id].phone == "(602) 555-0199"  # nothing kept that wasn't saved


def test_delete_renter_at_once_with_undo(win, qapp):
    sam = next(c for c in win.lib.clients.values() if c.name == "Sam Ortiz")
    win.open("renters", sam.id)
    win.renters.delete_wanted.emit(sam.id)
    assert sam.id not in win.lib.clients and win.renters.c is None
    assert [r.text(1) for r in win.renter_table.record_rows()] == ["Alex Rivera"]
    win.undo()
    assert sam.id in win.lib.clients


def test_a_rentals_renter_opens_on_the_renters_page(win, qapp):
    alex = _alex(win)
    r = next(r for r in win.lib.rentals.values() if r.client.id == alex.id)
    win.open("rentals", r.id)
    win.edit_client(False)  # the rental's Edit…
    assert win.view_key == "renters" and win.renters.current_id() == alex.id


def test_a_new_renter_is_a_sheet_then_opens_on_the_page(win, qapp, monkeypatch):
    from bodega.ui.dialogs.client import ClientDialog

    def fill(d):
        d.name.setText("Jo Park")
        d._save()
        return ClientDialog.DialogCode.Accepted

    monkeypatch.setattr(ClientDialog, "exec", fill)
    win.go("renters")
    win.new_here()
    jo = next(c for c in win.lib.clients.values() if c.name == "Jo Park")
    assert win.renters.current_id() == jo.id and "Jo Park" in [r.text(1) for r in win.renter_table.record_rows()]
    monkeypatch.setattr(ClientDialog, "exec", lambda d: ClientDialog.DialogCode.Rejected)
    n = len(win.lib.clients)
    win.new_here()  # closed without saving: nothing kept
    assert len(win.lib.clients) == n
