"""Tidy Up Renters (the standard's C-88): renters' names, companies, addresses and cities put in proper case by rule,
shown before and after first, the way Tidy Up Groups does gear.

A renter typed fast or brought in from a sheet reads "ALEX RIVERA", "northwind media llc", "88 example st ne". The
rule only touches a word typed all in capitals or all in small letters (one written in mixed case, "McKenzie" or
"iPhone", was typed that way on purpose), and keeps the words a business writes its own way: short capitals (LLC, NE,
ABC), P.O. Box, ordinals (1st, 22nd), Inc., Ltd. Emails come out in small letters, postcodes and state codes in
capitals. Nothing else changes: phones and notes stay as typed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bodega.core.model import Client

# words a business writes its own way, whatever case they were typed in
KEEP = {
    "llc": "LLC",
    "llp": "LLP",
    "lp": "LP",
    "inc": "Inc",
    "inc.": "Inc.",
    "ltd": "Ltd",
    "ltd.": "Ltd.",
    "co": "Co",
    "co.": "Co.",
    "corp": "Corp",
    "corp.": "Corp.",
    "plc": "PLC",
    "gmbh": "GmbH",
    "p.o.": "P.O.",
    "po": "PO",
    "usa": "USA",
    "us": "US",
    "uk": "UK",
    "tv": "TV",
    "dp": "DP",
    "ne": "NE",
    "nw": "NW",
    "se": "SE",
    "sw": "SW",
    "ii": "II",
    "iii": "III",
    "iv": "IV",
}
SMALL = {"of", "and", "the", "de", "la", "del", "van", "von", "du", "da", "for", "at", "on", "in", "y"}
ORDINAL = re.compile(r"^(\d+)(st|nd|rd|th)$", re.IGNORECASE)
CASED = ("name", "company", "address", "city")  # proper case
FIELD_WORDS = {
    "name": "Name",
    "company": "Company",
    "address": "Street",
    "city": "City",
    "region": "State",
    "postal": "ZIP Code",
    "email": "Email",
}


@dataclass
class Change:
    client_id: str
    field: str
    old: str
    new: str

    @property
    def label(self) -> str:
        return FIELD_WORDS.get(self.field, self.field)


def _word(w: str, first: bool, shouting: bool) -> str:
    """One word in proper case (see the module's words); a word typed in mixed case stays as it was. `shouting`: the
    whole line is in capitals, so short capitals there aren't acronyms (88 EXAMPLE ST → 88 Example St)."""
    letters = [c for c in w if c.isalpha()]
    if not letters or (not w.isupper() and not w.islower()):
        return w  # numbers and marks, or mixed case: as typed
    key = w.lower()
    if key in KEEP:
        return KEEP[key]
    if m := ORDINAL.match(w):
        return m.group(1) + m.group(2).lower()
    if any(c.isdigit() for c in w):
        return w.upper()  # a unit or a suite: 4B, B12
    if w.isupper() and len(letters) <= 3 and not first and not shouting:
        return w  # short capitals among other words: an acronym (ABC Studios)
    if key in SMALL and not first:
        return key
    # each part of a hyphenated or apostrophe'd word: Mary-Jane, O'Brien
    return re.sub(r"[^\W\d_]+", lambda m: m.group(0)[:1].upper() + m.group(0)[1:].lower(), w)  # (any letters: São)


def proper(text: str) -> str:
    """`text` in proper case, a line at a time (an address has more than one)."""
    lines = []
    for line in text.split("\n"):
        words = line.split(" ")
        shouting = any(c.isalpha() for c in line) and line.upper() == line
        out: list[str] = []
        first = True
        for w in words:
            if not w:
                out.append(w)
                continue
            out.append(_word(w, first, shouting))
            first = False
        lines.append(" ".join(out))
    fixed = "\n".join(lines)
    return re.sub(r"\b(P\.?O\.?)\s+box\b", lambda m: "P.O. Box", fixed, flags=re.IGNORECASE)


def tidy(c: Client) -> dict[str, str]:
    """What this renter's fields would read once tidied (only the ones that change)."""
    out: dict[str, str] = {}
    for field in CASED:
        was = getattr(c, field)
        now = proper(was)
        if now != was:
            out[field] = now
    if c.email.strip() and c.email.strip().lower() != c.email:
        out["email"] = c.email.strip().lower()
    for field in ("postal", "region"):
        was = getattr(c, field)
        if was.strip() and was.strip().upper() != was:
            out[field] = was.strip().upper()
    return out


def changes(clients: dict[str, Client]) -> list[Change]:
    """Every change Tidy Up Renters would make, renter by renter in name order."""
    out = []
    for c in sorted(clients.values(), key=lambda c: (c.name or c.company).casefold()):
        for field, new in tidy(c).items():
            out.append(Change(c.id, field, getattr(c, field), new))
    return out
