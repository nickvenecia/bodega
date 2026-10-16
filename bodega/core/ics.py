"""Rentals as a calendar file (.ics), for Apple Calendar, Google Calendar, Outlook: a pickup and a return
event for each rental that's booked, out or back (one pair per date range when lines have their own dates).

Every event keeps the same ID (the rental's id), and its SEQUENCE grows when the rental changes, so adding the
file again updates the events instead of adding copies. A cancelled rental's events say CANCELLED.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from bodega.core import pricing

PRODID = "-//Bodega//Rentals//EN"


def _esc(text: str) -> str:
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def _fold(line: str) -> str:
    """Lines longer than 75 bytes continue on the next line after a space (as the format asks)."""
    out: list[str] = []
    cur = b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > (75 if not out else 74):
            out.append(cur.decode("utf-8"))
            cur = b""
        cur += b
    out.append(cur.decode("utf-8"))
    return "\r\n ".join(out)


def _day(d: date) -> str:
    return d.strftime("%Y%m%d")


def _sequence(r) -> int:
    """Grows each time the rental is saved (minutes since 2020)."""
    try:
        t = datetime.fromisoformat(r.updated)
    except (TypeError, ValueError):
        return 0
    return max(0, int((t - datetime(2020, 1, 1)).total_seconds() // 60))


def events(lib, r) -> list[list[str]]:
    who = r.client.company or r.client.name or ""
    title = " · ".join(x for x in (r.number, who) if x)
    gear = [
        f"{line.qty} × {pricing.line_name(lib, line)}" if line.qty > 1 else pricing.line_name(lib, line)
        for line in r.lines
        if line.kind != "fee"
    ]
    about = "\n".join([r.project] if r.project else []) + ("\n" if r.project else "") + "\n".join(gear)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = []
    for n, (a, z) in enumerate(pricing.periods(r)):
        for kind, d in (("pickup", a), ("return", z)):
            if d is None:
                continue
            out.append(
                [
                    "BEGIN:VEVENT",
                    f"UID:{r.id}-{n}-{kind}@bodega",
                    f"DTSTAMP:{stamp}",
                    f"SEQUENCE:{_sequence(r)}",
                    f"DTSTART;VALUE=DATE:{_day(d)}",
                    f"DTEND;VALUE=DATE:{_day(d + timedelta(days=1))}",
                    f"SUMMARY:{_esc(('Pickup: ' if kind == 'pickup' else 'Return: ') + title)}",
                    f"DESCRIPTION:{_esc(about)}",
                    f"STATUS:{'CANCELLED' if r.is_cancelled() else 'CONFIRMED'}",
                    "TRANSP:TRANSPARENT",  # an all-day note, not a busy block
                    "END:VEVENT",
                ]
            )
    return out


def calendar(lib, rentals=None) -> str:
    """The .ics text for these rentals (or every booked, out, returned or cancelled one)."""
    chosen = rentals if rentals is not None else [r for r in lib.ordered_rentals() if r.past_quote()]
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:Bodega Rentals",
    ]
    for r in chosen:
        for ev in events(lib, r):
            lines += ev
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(x) for x in lines) + "\r\n"
