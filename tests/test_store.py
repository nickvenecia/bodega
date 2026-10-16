"""Saving and loading (core/store.py), and the made-up sample."""

from __future__ import annotations

import json

from bodega.core import dates, sample
from bodega.core.model import Item, Rental
from bodega.core.store import Library


def test_everything_saved_reads_back_the_same(data_folder):
    lib = sample.fill(Library(data_folder).load())
    again = Library(data_folder).load()
    assert len(again.items) == len(lib.items)
    assert len(again.packages) == 1 and len(again.rentals) == 1 and len(again.clients) == 1
    r = next(iter(again.rentals.values()))
    assert any(ln.pickup for ln in r.lines)  # line dates survive
    assert any(i.parent for i in again.items.values())


def test_unreadable_file_is_set_aside(data_folder):
    data_folder.mkdir(parents=True)
    (data_folder / "gear.json").write_text("{not json", encoding="utf-8")
    lib = Library(data_folder).load()
    assert lib.items == {}
    assert any(p.name.startswith("gear.json.unreadable-") for p in data_folder.iterdir())


def test_files_from_an_older_bodega_open_with_every_field_filled(data_folder):
    data_folder.mkdir(parents=True)
    (data_folder / "gear.json").write_text(
        json.dumps([{"id": "a", "name": "Old", "qty": "3", "future": 1}]), encoding="utf-8"
    )
    it = Library(data_folder).load().items["a"]
    assert it.qty == 3 and it.rentable and it.status == "ready"


def test_delete_item_frees_what_was_attached(data_folder):
    lib = sample.fill(Library(data_folder).load())
    fx6 = next(i for i in lib.items.values() if i.name.startswith("Sony FX6"))
    kids = [i for i in lib.items.values() if i.parent == fx6.id]
    lib.delete_item(fx6.id)
    assert all(not k.parent for k in kids)
    assert all(ln.item_id != fx6.id for p in lib.packages.values() for ln in p.lines)


def test_numbers_count_up_per_year(data_folder):
    lib = sample.fill(Library(data_folder).load())
    b = next(iter(lib.businesses.values()))
    first = next(iter(lib.rentals.values())).number
    second = lib.new_rental(b).number
    assert first.startswith("JLF-") and int(second.rsplit("-", 1)[1]) == int(first.rsplit("-", 1)[1]) + 1


def test_a_deleted_rentals_number_is_never_given_again(data_folder):
    lib = sample.fill(Library(data_folder).load())
    b = next(iter(lib.businesses.values()))
    newest = lib.new_rental(b)
    lib.delete_rental(newest.id)
    assert lib.new_rental(b).number != newest.number
    again = Library(data_folder).load()  # it stays spent after Bodega opens again
    assert again.new_rental(b).number not in (newest.number, *(r.number for r in lib.rentals.values()))


def test_a_number_from_before_this_stays_spent_once_its_rental_goes(data_folder):
    lib = sample.fill(Library(data_folder).load())
    b = next(iter(lib.businesses.values()))
    r = next(iter(lib.rentals.values()))
    lib.settings.pop("numbers", None)  # a data folder from an older Bodega
    lib.delete_rental(r.id)
    assert lib.new_rental(b).number != r.number


def test_a_quote_keeps_its_number_when_its_dates_move_into_another_year(data_folder):
    lib = sample.fill(Library(data_folder).load())
    b = next(iter(lib.businesses.values()))
    r = lib.new_rental(b)
    was = r.number
    r.pickup = f"{int(r.pickup[:4]) + 1}{r.pickup[4:]}"
    assert not lib.renumber(r) and r.number == was


def test_a_quote_moved_to_another_profile_takes_its_series_and_the_old_number_stays_spent(data_folder):
    from bodega.core.model import Business

    lib = sample.fill(Library(data_folder).load())
    b = next(iter(lib.businesses.values()))
    other = lib.add_business(Business(name="Second Unit", prefix="SU"))
    r = lib.new_rental(b)
    was = r.number
    r.business_id = other.id
    assert lib.renumber(r) and r.number.startswith("SU-")
    assert lib.new_rental(b).number != was


def test_next_number_carries_a_series_on_and_never_goes_back(data_folder):
    lib = sample.fill(Library(data_folder).load())
    b = next(iter(lib.businesses.values()))
    year = int(lib.new_rental(b).number.split("-")[1])
    assert lib.set_next_number(b, 48, year)
    assert lib.new_rental(b).number == f"{b.prefix}-{year}-048"
    assert not lib.set_next_number(b, 12, year)  # 12 was given already
    assert lib.new_rental(b).number == f"{b.prefix}-{year}-049"


def test_a_typed_number_another_rental_has_is_found(data_folder):
    lib = sample.fill(Library(data_folder).load())
    b = next(iter(lib.businesses.values()))
    first = next(iter(lib.rentals.values()))
    r = lib.new_rental(b)
    assert lib.number_taken(r.number, skip=r.id) is None
    assert lib.number_taken(f" {first.number.lower()} ", skip=r.id) is first
    assert lib.number_taken(first.number, skip=first.id) is None


def test_duplicate_rental_is_a_quote(data_folder):
    lib = sample.fill(Library(data_folder).load())
    src = next(iter(lib.rentals.values()))
    copy = lib.duplicate_rental(src)
    assert copy.status == "quote" and copy.id != src.id and len(copy.lines) == len(src.lines)
    copy.lines[0].qty = 9
    assert src.lines[0].qty == 1


def test_attached_item_cant_loop(data_folder):
    lib = Library(data_folder).load()
    a, b = Item(name="A"), Item(name="B")
    a.parent, b.parent = b.id, a.id
    lib.add_item(a)
    lib.add_item(b)
    from bodega.core import pricing

    assert pricing.root_of(lib, a) in (a, b)  # no endless loop
    assert len(pricing.with_attached(lib, a, 1)) == 2


def test_renter_edits_reach_quotes_only(data_folder):
    lib = sample.fill(Library(data_folder).load())
    c = next(iter(lib.clients.values()))
    r = next(iter(lib.rentals.values()))
    q = Rental(client=c, status="quote")
    lib.save_rental(q)
    c.email = "new@example.com"
    lib.save_client(c)
    assert lib.rentals[q.id].client.email == "new@example.com"
    assert lib.rentals[r.id].client.email == "new@example.com"  # booked follows too
    r.status = "out"
    c.phone = "1"
    lib.save_client(c)
    assert lib.rentals[r.id].client.phone != "1"


def test_groups_keep_your_order_and_follow_their_gear(tmp_path):
    from bodega.core.model import Item

    lib = Library(tmp_path).load()
    a = lib.add_item(Item(name="Pelican 1615", group="Body"))
    b = lib.add_item(Item(name="FX6", group="Body"))
    c = lib.add_item(Item(name="Cage", group="Body", parent=b.id))
    lib.add_group("Cases")
    assert lib.groups() == ["Body", "Cases"]  # an empty one stays
    lib.put_in_group([a.id], "Cases")
    assert a.group == "Cases"
    lib.put_in_group([b.id], "Cameras")
    assert c.group == "Cameras"  # what goes with it comes along
    assert "Body" not in lib.groups()  # the move emptied it
    lib.rename_group("Cameras", "Cinema Cameras")
    assert b.group == c.group == "Cinema Cameras"
    lib.step_group("Cinema Cameras", -1)
    assert lib.groups()[0] == "Cinema Cameras"
    assert lib.ordered_items()[0] is b
    lib.rename_group("Cases", "Cinema Cameras")  # merging
    assert a.group == "Cinema Cameras" and lib.groups() == ["Cinema Cameras"]
    lib.remove_group("Cinema Cameras")
    assert a.group == "" and not lib.groups()
    again = Library(tmp_path).load()
    assert again.items[a.id].group == ""


def test_tidy_up_groups_suggests_the_usual_names(tmp_path):
    from bodega.core import tidy
    from bodega.core.model import Item

    lib = Library(tmp_path).load()
    card = lib.add_item(Item(name="Sony 128GB SF-M Tough Series UHS-II SDXC Memory Card", group="SD Cards"))
    light = lib.add_item(Item(name="Aputure STORM 1000c LED Monolight with Wide Reflector", group="1000c"))
    fres = lib.add_item(Item(name="Aputure CF12 Fresnel", group="1000c", parent=light.id))
    case = lib.add_item(Item(name="Pelican 1615AirWD Wheeled Hard Case", group="Body"))
    odd = lib.add_item(Item(name="Mystery Thing", group="Steel"))
    new = tidy.suggest(lib.items)
    assert new[card.id] == "Media" and new[light.id] == new[fres.id] == "Lights"
    assert new[case.id] == "Cases & Carts" and new[odd.id] == "Grip"  # by the old name when the name says nothing
    assert lib.apply_groups(new) == 5
    assert lib.groups() == ["Media", "Lights", "Grip", "Cases & Carts"]  # in the tidy order


def test_your_order_and_companies(tmp_path):
    from bodega.core.model import Item

    lib = Library(tmp_path).load()
    a = lib.add_item(Item(name="Aputure STORM 80c", department="G&E", group="Lights"))
    b = lib.add_item(Item(name="amaran PT4c", department="G&E", group="Lights"))
    c = lib.add_item(Item(name="Matthews C-Stand", department="G&E", group="Steel"))
    assert lib.guess_brands() == 3 and a.brand == "Aputure" and lib.brands() == ["amaran", "Aputure", "Matthews"]
    lib.reorder_items([b.id], a.id)
    assert [i.name for i in lib.ordered_items()][:2] == ["amaran PT4c", "Aputure STORM 80c"]
    lib.reorder_items([c.id], a.id, after=True)  # next to a light: into Lights
    assert c.group == "Lights" and [i.id for i in lib.ordered_items()] == [b.id, a.id, c.id]
    again = Library(tmp_path).load()
    assert [i.id for i in again.ordered_items()] == [b.id, a.id, c.id] and again.items[a.id].brand == "Aputure"


def test_a_new_year_starts_its_numbers_again_at_001(data_folder):
    lib = sample.fill(Library(data_folder).load())
    b = next(iter(lib.businesses.values()))
    year = dates.today().year
    this = lib.next_number(b, year)
    assert lib.next_number(b, year + 1).endswith(f"-{year + 1}-001")  # a fresh series each year…
    lib._issue(b, year + 1)
    assert lib.next_number(b, year) == this  # …and this year's carries on where it was
