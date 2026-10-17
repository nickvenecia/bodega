"""Contrast on the drawn pages (the standard's 7.6 and A-01), not only on the color tokens: every visible label and
word button on the main places, a record's panel, Settings and a sheet, in the light and the dark look, reads at 4.5:1
against what's actually drawn behind it (3:1 for large text). The words' color is the one Qt draws them in; what's
behind is the color most of the visible area is, in a picture of the window."""

from __future__ import annotations

from collections import Counter

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QFontInfo, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractButton, QLabel, QWidget

from bodega.core import sample
from bodega.core.store import Library
from bodega.ui.style import tokens
from tests.ui import keep_size

# Words the standard lets read lower, and why
EXEMPT = {
    "Avatar": "the profile's initials in its monogram: decoration beside the profile's full name",
    "SideSearch": "the sidebar's search field's placeholder (placeholders may be text-faint, 3.2:1)",
}


def luminance(c: QColor) -> float:
    def ch(v: int) -> float:
        x = v / 255
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(c.red()) + 0.7152 * ch(c.green()) + 0.0722 * ch(c.blue())


def ratio(a: QColor, b: QColor) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def large(w: QWidget) -> bool:
    """WCAG's large text: 18 points (24 pixels), or 14 points (18.66 pixels) bold."""
    info = QFontInfo(w.font())
    return info.pixelSize() >= 24 or (info.pixelSize() >= 18.66 and w.font().weight() >= 600)


def faint_words(top: QWidget) -> list[tuple]:
    """Every visible label and word button in `top` that reads below its mark: (ratio, name, words, ink, behind)."""
    img = top.grab().toImage()
    out = []
    words = [*top.findChildren(QLabel), *(b for b in top.findChildren(QAbstractButton) if b.text().strip())]
    for w in words:
        if not w.isVisible() or not w.text().strip() or not w.isEnabled() or w.window() is not top:
            continue
        if w.objectName() in EXEMPT:
            continue
        seen = w.visibleRegion().boundingRect()  # (scrolled out of sight: not checked)
        r = QRect(w.mapTo(top, seen.topLeft()), seen.size()).intersected(img.rect())
        if r.width() < 6 or r.height() < 6:
            continue
        counts = Counter(
            img.pixel(x, y) for x in range(r.left(), r.right() + 1, 2) for y in range(r.top(), r.bottom() + 1, 2)
        )
        behind = QColor.fromRgb(counts.most_common(1)[0][0])
        role = w.foregroundRole() if isinstance(w, QLabel) else QPalette.ColorRole.ButtonText
        ink = w.palette().color(role)
        need = 3.0 if large(w) else 4.5
        got = ratio(ink, behind)
        if got < need:
            out.append((round(got, 2), w.objectName() or type(w).__name__, w.text()[:40], ink.name(), behind.name()))
    return sorted(set(out))


@pytest.fixture
def win(qapp, data_folder, monkeypatch):
    from bodega.ui.window.main_window import MainWindow

    monkeypatch.setenv("BODEGA_REDUCE_MOTION", "1")
    w = MainWindow(sample.fill(Library(data_folder).load()))
    keep_size(w)
    w.resize(1280, 800)
    w.show()
    QTest.qWait(50)
    yield w
    w.set_look("dark")
    w.close()


@pytest.mark.parametrize("look", ["light", "dark"])
def test_every_word_on_the_main_pages_reads(win, look):
    win.set_look(look)
    lib = win.lib
    found = {}
    for place in ("gear", "kits", "rentals", "calendar"):
        win.go(place)
        QTest.qWait(30)
        found[place] = faint_words(win)
    win.go("gear")
    win.open("gear", next(iter(win.gear_table.showing_rows())).data(0, 256))
    QTest.qWait(50)
    found["a piece"] = faint_words(win)
    win.open("packages", next(iter(lib.packages)))
    QTest.qWait(50)
    found["a kit"] = faint_words(win)
    win.open("rentals", next(iter(lib.rentals)))
    QTest.qWait(50)
    found["a rental"] = faint_words(win)
    assert not any(found.values()), {k: v for k, v in found.items() if v}


@pytest.mark.parametrize("look", ["light", "dark"])
def test_every_word_in_settings_and_a_sheet_reads(win, look):
    from bodega.ui.dialogs.client import ClientDialog
    from bodega.ui.dialogs.settings import SettingsDialog

    win.set_look(look)
    found = {}
    d = SettingsDialog(win.lib, win)
    d.show()
    QTest.qWait(30)
    for pane in d.panes:
        d.show_pane(pane)
        QTest.qWait(30)
        found[pane] = faint_words(d)
    d.done(0)
    r = next(iter(win.lib.rentals.values()))
    c = ClientDialog(r.client, False, win)
    c.show()
    QTest.qWait(30)
    found["renter"] = faint_words(c)
    c.done(0)
    assert not any(found.values()), {k: v for k, v in found.items() if v}


def test_every_accent_reads_on_a_chosen_row(qapp):
    """The words on a chosen row's wash (the sidebar's place) read for every accent, light and dark."""
    try:
        for key in tokens.ACCENTS:
            for scheme in ("light", "dark"):
                tokens.use(scheme, key)
                wash = tokens.solid(tokens.ACCENT_TINT, tokens.solid(tokens.GLASS, tokens.BG))
                for k in ("SOFT_TEXT", "SOFT_MUTED", "SOFT_WARN", "SOFT_BAD"):
                    assert tokens.contrast(getattr(tokens, k), wash) >= 4.5, (key, scheme, k)
    finally:
        tokens.use("dark", tokens.APP_ACCENT)
