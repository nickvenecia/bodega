"""Dates as people type them into a date field."""

from __future__ import annotations

from datetime import date, timedelta

from bodega.core import dates


def test_a_typed_date_reads_the_ways_people_write_one():
    around = date(2026, 10, 16)
    for text, want in (
        ("10/16", date(2026, 10, 16)),
        ("10/16/26", date(2026, 10, 16)),
        ("10/16/2027", date(2027, 10, 16)),
        ("Oct 16", date(2026, 10, 16)),
        ("oct 16 2026", date(2026, 10, 16)),
        ("16 Oct", date(2026, 10, 16)),
        ("October 16, 2026", date(2026, 10, 16)),
        ("2026-10-16", date(2026, 10, 16)),
    ):
        assert dates.typed(text, around) == want, text
    assert dates.typed("today") == dates.today()
    assert dates.typed("tomorrow") == dates.today() + timedelta(days=1)


def test_a_typed_date_without_a_year_is_the_one_nearest_the_field():
    assert dates.typed("1/5", date(2026, 12, 20)) == date(2027, 1, 5)  # booking in December for January
    assert dates.typed("12/28", date(2027, 1, 3)) == date(2026, 12, 28)
    assert dates.typed("2/29", date(2027, 6, 1)) == date(2028, 2, 29)  # the leap year nearest


def test_half_a_date_isnt_one_yet():
    for text in ("", "1", "10/", "Oct", "13/40", "Octo 16", "2/30/2026", "16 17 Oct", "hello"):
        assert dates.typed(text, date(2026, 10, 16)) is None, text
