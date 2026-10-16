"""Reading files defensively (core/model.py's shared reader, store formats): odd values never stop Bodega
opening, what a newer Bodega wrote is kept, and a status Bodega doesn't know is read as the cautious one."""

from __future__ import annotations

import json
from dataclasses import fields

import pytest

from bodega.core import sample, store
from bodega.core.model import (
    Business,
    CheckRow,
    Client,
    Item,
    LogEntry,
    Package,
    PackageLine,
    Rental,
    RentalLine,
)
from bodega.core.store import Library

RECORDS = [LogEntry, Item, PackageLine, Package, Client, Business, RentalLine, CheckRow, Rental]
ODD = [7, 2.5, True, "", "abc", "12", None]


def _plain_fields(cls):
    blank = cls()
    return [
        f.name
        for f in fields(cls)
        if f.name != "newer"
        and not isinstance(getattr(blank, f.name), (list, dict))
        and not hasattr(getattr(blank, f.name), "to_dict")
    ]


@pytest.mark.parametrize("cls", RECORDS)
@pytest.mark.parametrize("odd", ODD)
def test_every_plain_field_of_every_record_reads_whatever_plain_value_it_holds(cls, odd):
    blank = cls()
    for name in _plain_fields(cls):
        got, want = getattr(cls.from_dict({name: odd}), name), getattr(blank, name)
        assert type(got) is type(want), f"{cls.__name__}.{name} = {odd!r} read as {got!r}"
    cls.from_dict(dict.fromkeys(_plain_fields(cls), odd)).to_dict()  # and writes back


@pytest.mark.parametrize("cls", RECORDS)
def test_a_list_where_a_plain_value_belongs_and_back_again_is_broken(cls):
    """…so the store skips the record and keeps its file aside (test_fixes)."""
    blank = cls()
    for f in fields(cls):
        if f.name == "newer":
            continue
        structured = isinstance(getattr(blank, f.name), list) or hasattr(getattr(blank, f.name), "to_dict")
        with pytest.raises(ValueError):
            cls.from_dict({f.name: 7 if structured else [7]})


def test_a_kit_named_with_a_number_opens(data_folder):
    data_folder.mkdir(parents=True, exist_ok=True)
    (data_folder / "packages.json").write_text(json.dumps([{"name": 5, "notes": 12.5, "lines": []}]), encoding="utf-8")
    lib = Library(data_folder).load()
    assert [p.name for p in lib.packages.values()] == ["5"]


def test_the_kit_shows_in_the_window(qapp, data_folder):
    from bodega.ui.window.main_window import MainWindow

    data_folder.mkdir(parents=True, exist_ok=True)
    (data_folder / "packages.json").write_text(json.dumps([{"name": 5, "notes": None}]), encoding="utf-8")
    w = MainWindow(Library(data_folder).load())  # used to stop Bodega opening
    w.go("kits")
    w.close()


def test_what_a_newer_bodega_wrote_is_kept(data_folder):
    lib = sample.fill(Library(data_folder).load())
    raw = json.loads((data_folder / "gear.json").read_text(encoding="utf-8"))
    raw[0]["warranty"] = {"until": "2027-10-01"}
    raw[0]["log"] = [{"date": "2026-10-01", "kind": "service", "by": "Rosa"}]
    (data_folder / "gear.json").write_text(json.dumps(raw), encoding="utf-8")
    r = next(iter(lib.rentals.values()))
    rf = data_folder / "rentals" / f"{r.id}.json"
    rd = json.loads(rf.read_text(encoding="utf-8"))
    rd["lines"][0]["insured"] = True
    rd["client"]["pronouns"] = "they/them"
    rf.write_text(json.dumps(rd), encoding="utf-8")

    lib = Library(data_folder).load()
    lib.save_items()
    lib.save_rental(lib.rentals[r.id])
    again = json.loads((data_folder / "gear.json").read_text(encoding="utf-8"))
    assert again[0]["warranty"] == {"until": "2027-10-01"} and again[0]["log"][0]["by"] == "Rosa"
    rd = json.loads(rf.read_text(encoding="utf-8"))
    assert rd["lines"][0]["insured"] is True and rd["client"]["pronouns"] == "they/them"


def test_a_rental_status_bodega_doesnt_know_holds_its_gear_and_stays_as_it_was(data_folder):
    lib = sample.fill(Library(data_folder).load())
    r = next(iter(lib.rentals.values()))
    rf = data_folder / "rentals" / f"{r.id}.json"
    rd = json.loads(rf.read_text(encoding="utf-8"))
    rd["status"] = "on_hold"
    rf.write_text(json.dumps(rd), encoding="utf-8")
    lib = Library(data_folder).load()
    r = lib.rentals[r.id]
    assert r.status == "booked" and r.holds_gear()
    lib.save_rental(r)
    assert json.loads(rf.read_text(encoding="utf-8"))["status"] == "on_hold"  # written back as it was
    r.status = "returned"
    lib.save_rental(r)
    assert json.loads(rf.read_text(encoding="utf-8"))["status"] == "returned"  # changed here: the new one


def test_a_gear_status_or_kit_pricing_bodega_doesnt_know_is_the_cautious_one():
    assert Item.from_dict({"status": "lent"}).status == "repair"  # not available
    p = Package.from_dict({"pricing": "tiered", "discount": "15"})
    assert p.pricing == "sum" and p.to_dict()["pricing"] == "tiered"


def test_the_folder_says_its_format(data_folder):
    lib = sample.fill(Library(data_folder).load())
    lib.save_settings()
    assert json.loads((data_folder / "settings.json").read_text(encoding="utf-8"))["format"] == store.FORMAT
    assert not Library(data_folder).load().newer_format


def test_a_folder_from_a_newer_bodega_is_said_and_keeps_its_format(data_folder):
    lib = sample.fill(Library(data_folder).load())
    lib.settings["format"] = store.FORMAT + 1
    lib.save_settings()
    lib = Library(data_folder).load()
    assert lib.newer_format
    lib.save_settings()
    assert json.loads((data_folder / "settings.json").read_text(encoding="utf-8"))["format"] == store.FORMAT + 1


def test_an_older_format_is_upgraded_one_step_at_a_time(data_folder, monkeypatch):
    lib = sample.fill(Library(data_folder).load())
    lib.settings["format"] = 1
    lib.save_settings()
    steps = []

    def step(lib):
        steps.append(1)
        for it in lib.items.values():
            it.notes = it.notes or "upgraded"

    monkeypatch.setattr(store, "FORMAT", 2)
    monkeypatch.setattr(store, "UPGRADES", {1: step})
    lib = Library(data_folder).load()
    assert steps == [1] and all(it.notes for it in lib.items.values())
    assert json.loads((data_folder / "settings.json").read_text(encoding="utf-8"))["format"] == 2
    assert Library(data_folder).load() and steps == [1]  # once
    assert list((data_folder / "backups").glob("Bodega * before-format-2.zip"))


def test_a_setting_of_the_wrong_kind_is_read_as_its_default():
    from bodega.core import settings

    assert settings.value({}, "appearance") == "system"
    assert settings.value({"appearance": 7}, "appearance") == "system"  # a hand-edited file: never a crash
    assert settings.value({"auto_update": "no"}, "auto_update") is True
    assert settings.value({"auto_update": False}, "auto_update") is False
    folded = settings.value({}, "folded")
    folded.append("x")
    assert settings.value({}, "folded") == []  # the default is never shared between readers
