"""How a search reads words: case and accents don't matter ("cafe" finds "Café", "ARRI" finds "Arri"), and every
word typed must be found somewhere in what's searched. No Qt here."""

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
