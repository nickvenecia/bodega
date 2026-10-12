"""Read a price off a product page (B&H, Adorama, a maker's store…), for Check Price on a piece of gear.

Stores put the price in the page for search engines: structured data (JSON-LD "offers"), or price meta tags.
Some stores block anything that isn't a browser; then there's no price and the caller says so. Nothing here
changes your gear: it only reads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from bodega.core import web
from bodega.core.log import get_logger

log = get_logger(__name__)

STORES = {
    "bhphotovideo.com": "B&H",
    "adorama.com": "Adorama",
    "amazon.com": "Amazon",
    "harborfreight.com": "Harbor Freight",
    "homedepot.com": "Home Depot",
    "guitarcenter.com": "Guitar Center",
    "sweetwater.com": "Sweetwater",
}


@dataclass
class Found:
    price: Decimal
    store: str
    currency: str = "USD"


def store_name(url: str) -> str:
    host = urlparse(url if "://" in url else "https://" + url).netloc.lower().removeprefix("www.")
    for domain, name in STORES.items():
        if host == domain or host.endswith("." + domain):
            return name
    return host


def _number(text) -> Decimal | None:
    if text is None:
        return None
    m = re.search(r"\d[\d,]*(?:\.\d+)?", str(text))
    if not m:
        return None
    try:
        n = Decimal(m.group(0).replace(",", ""))
    except InvalidOperation:
        return None
    return n if n > 0 else None


def _offers(node, out: list) -> None:
    """Walk JSON-LD for offers' prices (price, lowPrice), products first."""
    if isinstance(node, list):
        for x in node:
            _offers(x, out)
    elif isinstance(node, dict):
        offers = node.get("offers")
        if offers is not None:
            for o in offers if isinstance(offers, list) else [offers]:
                if isinstance(o, dict):
                    n = _number(o.get("price") or o.get("lowPrice"))
                    if n is None and isinstance(o.get("priceSpecification"), dict):
                        n = _number(o["priceSpecification"].get("price"))
                    if n is not None:
                        out.append((n, str(o.get("priceCurrency") or "USD")))
        for k, v in node.items():
            if k != "offers" and isinstance(v, (dict, list)):
                _offers(v, out)


def parse(html: str) -> tuple[Decimal, str] | None:
    """The product's price in a page, or None."""
    page = web.read(html)
    found: list[tuple[Decimal, str]] = []
    try:
        _offers(page.ld_json, found)
    except RecursionError:  # absurdly deep data
        found = []
    if found:
        return found[0]
    for key in ("product:price:amount", "og:price:amount", "price"):
        n = _number(page.meta.get(key))
        if n is not None:
            return n, "USD"
    for text in (page.item_price, page.offscreen_price):
        n = _number(text)
        if n is not None:
            return n, "USD"
    return None


def fetch(url: str) -> Found | None:
    """Download the page and read its price. Raises OSError when the page can't be reached (or the link
    isn't a public web page: see core/web.py)."""
    try:
        page = web.fetch(url)
    except web.Blocked:
        raise
    except OSError as e:
        raise OSError(str(e).replace(urlparse(web.web_link(url)).hostname or "?", store_name(url))) from e
    got = parse(page.html)
    if got is None:
        return None
    return Found(got[0], store_name(page.url), got[1])
