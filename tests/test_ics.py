"""Rentals as a calendar file (core/ics.py)."""

from __future__ import annotations

from bodega.core import ics, sample
from bodega.core.store import Library


def test_pickup_and_return_events(tmp_path):
    lib = sample.fill(Library(tmp_path).load())
    r = next(iter(lib.rentals.values()))
    r.status = "booked"
    r.project = "Night shoot; two days, maybe three\\"
    text = ics.calendar(lib)
    assert text.startswith("BEGIN:VCALENDAR\r\n") and text.endswith("END:VCALENDAR\r\n")
    n = text.count("BEGIN:VEVENT")
    assert n >= 2 and n % 2 == 0  # a pickup and a return for each date range
    assert f"UID:{r.id}-0-pickup@bodega" in text and "SUMMARY:Pickup: " in text
    assert r"Night shoot\; two days\, maybe three\\" in text.replace("\r\n ", "")
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))
    again = ics.calendar(lib)
    assert [x for x in again.split("\r\n") if x.startswith("UID")] == [
        x for x in text.split("\r\n") if x.startswith("UID")
    ]  # the same events, so adding it again updates them
    r.status = "cancelled"
    assert "STATUS:CANCELLED" in ics.calendar(lib)
    r.status = "quote"
    assert "BEGIN:VEVENT" not in ics.calendar(lib)
