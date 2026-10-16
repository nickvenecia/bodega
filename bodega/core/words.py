"""Words that change with a number: "1 piece", "2 pieces", never "1 pieces". No Qt here."""

from __future__ import annotations


def count(n: int, word: str, plural: str = "") -> str:
    """ "1 piece", "2 pieces", "1,200 pieces" (`plural` when it isn't just an s)."""
    return f"{n:,} {word if n == 1 else (plural or word + 's')}"
