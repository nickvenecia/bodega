"""Words that change with a number: "1 piece", "2 pieces", never "1 pieces". No Qt here."""

from __future__ import annotations


def count(n: int, word: str, plural: str = "") -> str:
    """ "1 piece", "2 pieces", "1,200 pieces" (`plural` when it isn't just an s)."""
    return f"{n:,} {word if n == 1 else (plural or word + 's')}"


def size(n: int) -> str:
    """A file's size as people say it: "820 KB", "1.4 MB" (a thousand to a kilobyte, as Finder counts)."""
    if n < 1000:
        return count(n, "byte")
    kb = n / 1000
    if kb < 999.5:
        return f"{kb:.0f} KB"
    mb = kb / 1000
    return f"{mb:.1f} MB" if mb < 999.95 else f"{mb / 1000:.1f} GB"
