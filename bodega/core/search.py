"""How a search reads words: case and accents don't matter ("cafe" finds "Café", "ARRI" finds "Arri"), and every
word typed must be found somewhere in what's searched. One function per kind of record says what's searched in it
(gear_hay, kit_hay, rental_hay), used by its list and by the command palette alike, so they find the same things.
No Qt here."""

from __future__ import annotations

import unicodedata


def folded(text: str) -> str:
    """`text` with its case and accents taken off, for comparing: "Café Señor" -> "cafe senor"."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


def words(typed: str) -> list[str]:
    """The words of a search, folded."""
    return folded(typed).split()


def matches(hay: str, wanted: list[str]) -> bool:
    """Every wanted word is in `hay` (already folded)."""
    return all(w in hay for w in wanted)


def gear_hay(it, goes_with: str = "") -> str:
    """What a piece is found by: its name, company, series, group, notes, serial numbers and what it goes with."""
    return folded(" ".join((it.name, it.brand, it.series, it.group, it.notes, " ".join(it.serials), goes_with)))


def kit_hay(p) -> str:
    """What a kit is found by: its name and notes."""
    return folded(p.name + " " + p.notes)


def renter_hay(c) -> str:
    """What a renter is found by: the person, the company, their email, phone and town."""
    return folded(" ".join((c.name, c.company, c.email, c.phone, c.city)))


def rental_hay(r) -> str:
    """What a rental is found by: its number, the renter (person and company) and the production."""
    return folded(" ".join((r.number, r.client.name, r.client.company, r.project)))
