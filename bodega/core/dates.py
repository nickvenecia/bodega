"""Dates the way Bodega shows them ("Oct 10, 2026"), the same on every computer."""

from __future__ import annotations

from datetime import date, timedelta

MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)  # fmt: skip
CAL_WEEKDAYS = (
    "Sun",
    "Mon",
    "Tue",
    "Wed",
    "Thu",
    "Fri",
    "Sat",
)  # a calendar's columns: Sunday first, like a wall calendar


def today() -> date:
    return date.today()


def parse(s: str) -> date | None:
    try:
        return date.fromisoformat(s.strip()) if s else None
    except ValueError:
        return None


def iso(d: date) -> str:
    return d.isoformat()


def fmt(d: date | None) -> str:
    """date(2026, 10, 10) -> "Oct 10, 2026" (the same on every computer, whatever its language)."""
    if d is None:
        return ""
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def fmt_moment(stamp: str) -> str:
    """ "2026-10-16T09:41:00" -> "Oct 16, 2026, 9:41 AM" ("" if it isn't a time)."""
    from datetime import datetime

    try:
        when = datetime.fromisoformat(str(stamp))
    except ValueError:
        return ""
    hour = when.hour % 12 or 12
    return f"{fmt(when.date())}, {hour}:{when.minute:02d} {'AM' if when.hour < 12 else 'PM'}"


def fmt_short(d: date | None) -> str:
    """date(2026, 10, 10) -> "Oct 10"."""
    if d is None:
        return ""
    return f"{MONTHS[d.month - 1]} {d.day}"


WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def fmt_day(d: date | None) -> str:
    """date(2026, 10, 9) -> "Fri, Oct 9, 2026"."""
    if d is None:
        return ""
    return f"{WEEKDAYS[d.weekday()]}, {fmt(d)}"


def span(a: date | None, b: date | None) -> str:
    """Two dates as a short range: "Oct 9–12, 2026", "Oct 30 – Nov 2, 2026", "Dec 30, 2026 – Jan 2, 2027"."""
    if a is None and b is None:
        return ""
    if a is None or b is None or a == b:
        return fmt(a or b)
    if a.year != b.year:
        return f"{fmt(a)} – {fmt(b)}"
    if a.month != b.month:
        return f"{fmt_short(a)} – {fmt_short(b)}, {b.year}"
    return f"{MONTHS[a.month - 1]} {a.day}–{b.day}, {a.year}"


def plus(d: date, days: int) -> date:
    return d + timedelta(days=days)


def _near(month: int, day: int, around: date) -> date | None:
    """That day in the year that puts it closest to `around` (a later one when it's a tie)."""
    best = None
    for year in (around.year - 1, around.year, around.year + 1):
        try:
            d = date(year, month, day)
        except ValueError:
            continue
        if best is None or abs((d - around).days) <= abs((best - around).days):
            best = d
    return best


def typed(text: str, around: date | None = None) -> date | None:
    """A date as people type one: "today", "tomorrow", "10/16", "10/16/26", "Oct 16", "16 Oct 2026",
    "October 16, 2026", "2026-10-16". Without a year, the one closest to `around` (the date the field had).
    None while it doesn't read as a date yet."""
    import re

    around = around or today()
    t = text.strip().lower().replace(",", " ").replace(".", " ")
    if not t:
        return None
    if t in ("today", "tod"):
        return today()
    if t in ("tomorrow", "tom", "tmrw"):
        return today() + timedelta(days=1)
    if t == "yesterday":
        return today() - timedelta(days=1)
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", t):
        try:
            return date(*(int(x) for x in t.split("-")))
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{2}|\d{4}))?", t)
    if m:
        month, day, year = int(m[1]), int(m[2]), m[3]
    else:
        words = t.split()
        names = {n.lower(): i + 1 for i, n in enumerate(MONTHS)} | {n.lower(): i + 1 for i, n in enumerate(MONTH_NAMES)}
        month = next((names[w] for w in words if w in names), 0)
        nums = [w for w in words if w.isdigit()]
        if not month or not nums or len(words) != 1 + len(nums) or len(nums) > 2:
            return None
        day = int(nums[0]) if len(nums[0]) <= 2 else 0
        year = None
        if len(nums) == 2:  # with its year, written out: "Oct 16 2026", or "2026 Oct 16"
            if len(nums[0]) == 4 and len(nums[1]) <= 2:
                day, year = int(nums[1]), nums[0]
            elif len(nums[1]) == 4:
                year = nums[1]
            else:
                return None
    if year is None:
        return _near(month, day, around)
    y = int(year) + (2000 if len(year) == 2 else 0)
    try:
        return date(y, month, day)
    except ValueError:
        return None
