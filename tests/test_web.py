"""How Bodega introduces itself to the sites a link points at (core/web.py)."""

from __future__ import annotations

from bodega.core import web


def test_bodega_says_what_it_is_to_every_site():
    """The owner's call: Bodega is an app and never passes itself off as a web browser."""
    ua = web.HEADERS["User-Agent"]
    assert ua.startswith("Bodega/") and not any(w in ua for w in ("Mozilla", "Chrome", "Safari", "Gecko"))
