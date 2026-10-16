"""Tidy Up Renters (the standard's C-88): proper case by rule, keeping a business's own words, shown first, applied as
one change after a safety copy; rentals not out the door yet follow, as they do a renter edit."""

from __future__ import annotations

from dataclasses import replace

import pytest

from bodega.core import sample, tidy_renters
from bodega.core.model import Client
from bodega.core.store import Library


@pytest.mark.parametrize(
    ("typed", "tidied"),
    [
        ("ALEX RIVERA", "Alex Rivera"),
        ("northwind media llc", "Northwind Media LLC"),
        ("88 EXAMPLE ST NE", "88 Example St NE"),
        ("po box 12", "P.O. Box 12"),
        ("My ABC Studios", "My ABC Studios"),  # short capitals among other words: an acronym
        ("mary-jane o'brien", "Mary-Jane O'Brien"),
        ("McKenzie iPhone", "McKenzie iPhone"),  # mixed case: typed that way on purpose
        ("unit 4b, 22ND st", "Unit 4B, 22nd St"),
        ("bank of america", "Bank of America"),
        ("THE ROYAL FILM CO.", "The Royal Film Co."),
        ("são paulo", "São Paulo"),
        ("12 main st\nsuite 4b", "12 Main St\nSuite 4B"),
    ],
    ids=lambda v: v.replace("\n", "/")[:20],
)
def test_proper_case_keeps_a_business_own_words(typed, tidied):
    assert tidy_renters.proper(typed) == tidied


def test_emails_postcodes_and_states_and_nothing_else():
    c = Client(name="Alex Rivera", email=" Alex@Northwind.Example", postal="sw1a 1aa", region="tx", phone="(602) x5")
    assert tidy_renters.tidy(c) == {"email": "alex@northwind.example", "postal": "SW1A 1AA", "region": "TX"}
    assert tidy_renters.tidy(Client(name="Alex Rivera", city="Phoenix")) == {}


def test_tidying_is_one_change_with_a_safety_copy_and_bookings_follow(data_folder):
    lib = sample.fill(Library(data_folder).load())
    r = next(iter(lib.rentals.values()))
    shouty = lib.save_client(replace(r.client, name="ALEX RIVERA", city="PHOENIX"))
    r.client = replace(shouty)
    lib.save_rental(r)
    found = tidy_renters.changes(lib.clients)
    assert {(c.field, c.new) for c in found if c.client_id == shouty.id} >= {
        ("name", "Alex Rivera"),
        ("city", "Phoenix"),
    }
    before = set((data_folder / "backups").glob("*")) if (data_folder / "backups").exists() else set()
    assert lib.tidy_clients(found) >= 1
    assert lib.clients[shouty.id].name == "Alex Rivera"
    assert set((data_folder / "backups").glob("*")) - before  # a safety copy first
    again = Library(data_folder).load()
    rental = again.rentals[r.id]
    assert (rental.client.name == "Alex Rivera") == rental.ahead()  # a booking follows; one that's out keeps its copy


def test_tidy_up_renters_from_the_profile_menu(qapp, data_folder, monkeypatch):
    from bodega.ui.dialogs import common
    from bodega.ui.window.main_window import MainWindow

    lib = sample.fill(Library(data_folder).load())
    c = next(iter(lib.clients.values()))
    lib.save_client(replace(c, company="northwind media llc"))
    w = MainWindow(lib)
    shown = []
    monkeypatch.setattr(common, "tidy_renters_preview", lambda parent, found, names: shown.append(found) or True)
    menu = next(a.menu() for a in w.menuBar().actions() if a.text() == "Profile")
    next(a for a in menu.actions() if a.text() == "Tidy Up Renters…").trigger()
    assert shown and lib.clients[c.id].company == "Northwind Media LLC"
    w.close()
