"""Reading a price off a product page (no network: pages are made up here)."""

from __future__ import annotations

from decimal import Decimal

from bodega.core import prices, web


def test_json_ld_offer():
    html = """<html><head><script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Product","name":"Camera",
     "offers":{"@type":"Offer","price":"5498.00","priceCurrency":"USD"}}
    </script></head></html>"""
    assert prices.parse(html) == (Decimal("5498.00"), "USD")


def test_json_ld_list_and_low_price():
    html = """<script type='application/ld+json'>[{"@type":"BreadcrumbList"},
    {"@type":"Product","offers":[{"@type":"AggregateOffer","lowPrice":"1,299.99"}]}]</script>"""
    assert prices.parse(html)[0] == Decimal("1299.99")


def test_meta_tags():
    assert prices.parse('<meta property="product:price:amount" content="279.00">')[0] == Decimal("279.00")
    assert prices.parse('<meta content="64.99" itemprop="price">')[0] == Decimal("64.99")


def test_nothing_there():
    assert prices.parse("<html><body>Sold out</body></html>") is None
    assert prices.parse('<script type="application/ld+json">{not json</script>') is None


def test_store_names():
    assert web.site_name("https://www.bhphotovideo.com/c/product/1.html") == "B&H"
    assert web.site_name("tilta.com/x") == "tilta.com"
