"""Addresses (the standard's 4.6, core/addresses.py and the one address control)."""

from __future__ import annotations

from bodega.core import addresses, sample
from bodega.core.model import Business, Client
from bodega.core.store import Library
from tests.ui import button


def test_an_address_from_before_prints_as_it_was_typed():
    old = Client.from_dict({"name": "Lisa Kim", "address": "88 Example St\nPhoenix, AZ 85004"})
    assert old.country == "" and addresses.country_of(old.country) == "US"  # the home country
    assert addresses.of(old) == ["88 Example St", "Phoenix, AZ 85004"]


def test_an_address_prints_city_state_and_zip_and_a_foreign_country():
    assert addresses.lines("1200 Sample Ave", "Albuquerque", "NM", "87102") == [
        "1200 Sample Ave",
        "Albuquerque, NM 87102",
    ]
    assert addresses.lines("1 Front St W", "Toronto", "ON", "M5J 2X5", "CA") == [
        "1 Front St W",
        "Toronto, ON M5J 2X5",
        "Canada",
    ]
    assert addresses.lines("", "", "", "", "US") == []  # nothing typed: nothing printed


def test_a_region_is_one_of_its_countrys_own_or_refused():
    assert addresses.region_code("US", "Texas") == "TX" and addresses.region_code("", "tx") == "TX"
    assert addresses.region_code("US", "Ontario") is None  # not one of the country's: refused, never guessed
    assert addresses.region_code("CA", "ontario") == "ON"
    assert addresses.region_code("FR", "Île-de-France") == "Île-de-France"  # no list kept: as typed
    assert addresses.region_code("US", "") == ""


def test_the_region_is_read_from_the_postal_code():
    assert addresses.region_from_postal("US", "87102") == "NM"
    assert addresses.region_from_postal("US", "10001-2345") == "NY"
    assert addresses.region_from_postal("US", "96799") == "AS" and addresses.region_from_postal("US", "96701") == "HI"
    assert (
        addresses.region_from_postal("CA", "m5j 2x5") == "ON" and addresses.region_from_postal("CA", "X0A 0H0") == "NU"
    )
    assert addresses.region_from_postal("AU", "2600") == "ACT" and addresses.region_from_postal("AU", "2000") == "NSW"
    assert addresses.region_from_postal("US", "ABCDE") == "" and addresses.region_from_postal("GB", "SW1A 1AA") == ""


def test_the_agreement_prints_the_renters_and_profiles_address(data_folder):
    from bodega.core import document

    lib = sample.fill(Library(data_folder).load())
    r = next(iter(lib.rentals.values()))
    b = lib.businesses.get(r.business_id) or lib.pricing()
    v = document.build_rental(lib, r, b)
    renter = dict(v.blocks)["Renter"]
    assert "88 Example St\nPhoenix, AZ 85004" in renter
    assert any("1200 Sample Ave, Albuquerque, NM 87102" in line for line in v.contact)


def test_the_renter_form_has_the_one_address_control(qapp):
    from bodega.ui.components.address import AddressFields
    from bodega.ui.dialogs.client import ClientDialog
    from bodega.ui.dialogs.profile import ProfileDialog

    d = ClientDialog(Client(name="Lisa Kim", address="88 Example St\nPhoenix, AZ 85004"), True)
    a = d.address
    assert isinstance(a, AddressFields) and a.region_pick.isVisibleTo(d) and not a.region_text.isVisibleTo(d)
    assert a.country.currentData() == "US" and a.region_sec.label.text() == "State"
    assert not d.unsaved()  # an old address, untouched, isn't a change
    a.city.setText("Phoenix")
    a.postal.setText("85004")
    a.postal.textEdited.emit("85004")  # a ZIP code fills in the state while it's blank
    assert a.region() == "AZ" and d.unsaved()
    a.country.setCurrentIndex(a.country.findData("CA"))
    a.country.activated.emit(a.country.currentIndex())
    assert a.region() == "" and a.region_sec.label.text() == "Province"  # Arizona isn't one of Canada's
    a.country.setCurrentIndex(a.country.findData("FR"))
    a.country.activated.emit(a.country.currentIndex())
    assert a.region_text.isVisibleTo(d) and not a.region_pick.isVisibleTo(d)  # no list kept: typed
    a.region_text.setText("Île-de-France")
    button(d, "Save").click()
    c = d.client
    assert (c.city, c.region, c.postal, c.country) == ("Phoenix", "Île-de-France", "85004", "FR")
    p = ProfileDialog(Business(name="Juniper Lane Films"), True)
    assert isinstance(p.address, AddressFields)  # the same control on every form with an address
    p.deleteLater()
