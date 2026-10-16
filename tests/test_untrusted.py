"""Files and words from outside, read as untrusted: SVG logos, oversized sheets, slow pages, links in release
notes, and what the log keeps."""

from __future__ import annotations

import json
import logging

import pytest

from bodega.core import importer, svg, web

PICTURE = "/tmp/secret-scan.png"
HOSTILE = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="100" height="40" onload="alert(1)">
  <style>@import url(file:///etc/passwd);</style>
  <script>alert(1)</script>
  <image href="{PICTURE}" width="100" height="40"/>
  <image xlink:href="file://{PICTURE}" width="100" height="40"/>
  <use href="other.svg#logo"/>
  <foreignObject><p>hi</p></foreignObject>
  <rect width="100" height="40" fill="url(https://evil.example/x)" stroke="url(#grad)"/>
  <circle cx="20" cy="20" r="10" fill="#2F6FDB"/>
  <image href="data:image/png;base64,iVBORw0KGgo=" width="1" height="1"/>
  <use href="#dot"/>
</svg>"""


def test_an_svg_logo_keeps_only_its_drawing():
    out = svg.clean(HOSTILE.encode()).decode()
    for gone in (PICTURE, "onload", "@import", "<script", "other.svg", "foreignObject", "evil.example"):
        assert gone not in out, gone
    for kept in ("<circle", "#2F6FDB", "data:image/png;base64", 'href="#dot"', "url(#grad)"):
        assert kept in out, kept
    assert "<svg" in out and "ns0:" not in out  # still a plain SVG, as Qt reads it


def test_an_svg_with_a_doctype_is_refused():
    bomb = '<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "aaaa">]><svg xmlns="http://www.w3.org/2000/svg">&a;</svg>'
    with pytest.raises(svg.NotALogo, match="other files"):
        svg.clean(bomb.encode())


@pytest.mark.parametrize(
    "data",
    [b"\xff\xfe not text", b"<html></html>", b"<svg", b"x" * (svg.MAX_BYTES + 1)],
    ids=["not-text", "not-svg", "cut-off", "too-big"],  # (named, never by its bytes: see conftest's MAX_TEST_ID)
)
def test_something_that_isnt_a_usable_svg_is_said_plainly(data):
    with pytest.raises(svg.NotALogo):
        svg.clean(data)


def test_a_logo_from_before_is_drawn_from_its_cleaned_drawing(qapp, tmp_path):
    from PySide6.QtGui import QColor, QImage

    from bodega.doc.render import logo_size, svg_logo

    pic = QImage(10, 10, QImage.Format.Format_RGB32)
    pic.fill(QColor("#FF0000"))
    secret = tmp_path / "secret.png"
    pic.save(str(secret))
    logo = tmp_path / "old-logo.svg"  # kept as it came, by an older Bodega
    logo.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><image href="{secret}" '
        'width="10" height="10"/></svg>',
        encoding="utf-8",
    )
    r = svg_logo(logo)
    assert r is not None and logo_size(logo) == (10.0, 10.0)
    out = QImage(10, 10, QImage.Format.Format_ARGB32)
    out.fill(QColor(0, 0, 0, 0))
    from PySide6.QtGui import QPainter

    p = QPainter(out)
    r.render(p)
    p.end()
    assert out.pixelColor(5, 5).alpha() == 0  # the file from the computer never reached the page


@pytest.mark.qt_warnings  # (the planted parts of the SVG, which Qt can't find once they're cleaned out)
def test_adding_an_svg_logo_keeps_the_cleaned_one(qapp, data_folder, tmp_path):
    from bodega.core.paths import logos_dir
    from bodega.ui.dialogs.profile import import_logo

    src = tmp_path / "logo.svg"
    src.write_text(HOSTILE, encoding="utf-8")
    name = import_logo(src)
    kept = (logos_dir() / name).read_text(encoding="utf-8")
    assert PICTURE not in kept and "<circle" in kept


def test_a_sheet_too_big_to_be_a_gear_list_is_said_plainly(tmp_path, monkeypatch):
    monkeypatch.setattr(importer, "MAX_ROWS", 10)
    sheet = tmp_path / "huge.csv"
    sheet.write_text("Name,Qty\n" + "Light,1\n" * 20, encoding="utf-8")
    with pytest.raises(OSError, match="more than 10 rows"):
        importer.load_rows(sheet)
    wide = tmp_path / "wide.csv"
    wide.write_text(",".join(["x"] * (importer.MAX_COLUMNS + 1)), encoding="utf-8")
    with pytest.raises(OSError, match="columns"):
        importer.load_rows(wide)


def test_a_cell_longer_than_csv_allows_is_said_plainly(tmp_path):
    sheet = tmp_path / "long.csv"
    sheet.write_text('Name,Notes\nLight,"' + "x" * 200_000 + '"\n', encoding="utf-8")
    with pytest.raises(OSError, match="isn't laid out as a sheet"):
        importer.load_rows(sheet)


def test_a_page_that_trickles_in_is_stopped(monkeypatch):
    class Slow:
        status, headers = 200, {}

        def read(self, n):
            return b"x"  # forever, one byte at a time

    class Conn:
        def __init__(self, *a, **k):
            pass

        def request(self, *a, **k):
            pass

        def getresponse(self):
            return Slow()

        def close(self):
            pass

    clock = iter(range(0, 10_000))
    monkeypatch.setattr(web, "_PinnedHTTPS", Conn)
    monkeypatch.setattr(web.time, "monotonic", lambda: next(clock))
    with pytest.raises(TimeoutError):
        web._get("https://slow.example/", "93.184.216.34", 5, web.MAX_BYTES)


@pytest.mark.parametrize(
    ("url", "opens"),
    [
        ("https://github.com/nickvenecia/bodega/releases", True),
        ("http://github.com/x", False),
        ("javascript:alert(1)", False),
        ("file:///etc/passwd", False),
        ("https://user@evil.example/", False),
    ],
)
def test_links_in_release_notes_open_only_when_theyre_plain_web_links(qapp, monkeypatch, url, opens):
    from PySide6.QtGui import QDesktopServices

    from bodega.ui.dialogs import update

    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda u: opened.append(u.toString()))
    update.open_url(url)
    assert bool(opened) is opens


def test_the_log_is_one_json_line_each_without_names_or_paths(tmp_path):
    from bodega.core.log import _Lines

    record = logging.LogRecord("bodega.x", logging.WARNING, __file__, 1, "saved %s", ("a.pdf",), None)
    line = json.loads(_Lines().format(record))
    assert line["level"] == "warning" and line["where"] == "bodega.x" and line["what"] == "saved a.pdf"
