"""The standard's G.28 measurements (T-18), run over Bodega's places, a record of each kind, every Settings section and
a sheet, in the light and the dark look: sizes may not change between them. Bodega is a desktop app (the owner,
2026-10-16), so the pointer mode is the one there is; touch and phone don't apply. Each failure names the component,
the place and the look.

What's checked here, by number: 1 circles are square; 2 controls at their token; 3 rows at their token; 5 type from
the ramp only; 12 corners concentric; 13 disabled is 40%; 16 toasts' times; 17 no motion under Reduce Motion; 19 no
stray values (margins and gaps on the grid or a token). Lists and parent rows (14, 15) are tests/test_ticks.py and
tests/test_pieces.py; menus (9, 10, 11) tests/test_window.py; one left and right edge (7) tests/test_sizes.py."""

from __future__ import annotations

import re
from collections import Counter

import pytest
from PySide6.QtGui import QFontInfo
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedLayout,
    QToolButton,
    QWidget,
)

from bodega.core import sample
from bodega.core.store import Library
from bodega.ui.components import access
from bodega.ui.style import theme, tokens

RAMP = {
    tokens.TEXT_FOOTNOTE,
    tokens.TEXT_SUBHEAD,
    tokens.TEXT_CALLOUT,
    tokens.TEXT_BODY,
    tokens.TEXT_TITLE3,
    tokens.TEXT_TITLE2,
    tokens.TEXT_TITLE1,
    tokens.TEXT_LARGE_TITLE,
    tokens.TEXT_BRAND,  # (the wordmark: a mark, not words)
}
# The values a margin or gap may take: the 4-point grid, Apple's 2, 6, 10 and 14, and the standard's own values
# that are tokens (22 above a strip, 18 below the figures…)
TOKEN_VALUES = {v for k, v in vars(tokens).items() if k.isupper() and isinstance(v, int) and not isinstance(v, bool)}

# Controls that aren't at control-h, and why (G.2 and G.17 say what each is)
NOT_A_CONTROL = {
    "SegBtn": "a segment inside its control-h track (the track is checked)",
    "LinkBtn": "words that act as a link (Review…), not a capsule",
    "RecordStatus": "a record's status words in its head (G.17: a dot and a word)",
    "StatusLine": "a status line's words, there to be read aloud",
    "Disclosure": "a card's disclosure row: its title words and chevron",
}
OWN_HEIGHT = {"FilterChip": tokens.FILTER_CHIP_H}  # (G.10.6) (the top bar's search is bar-h: checked by itself)


def where(w: QWidget) -> str:
    chain = []
    while w is not None and len(chain) < 4:
        chain.append(w.objectName() or type(w).__name__)
        w = w.parentWidget()
    return "/".join(reversed(chain))


def measure(top: QWidget, place: str, look: str, found: list) -> Counter:
    """Run the checks on what `top` shows; return its sizes (to compare the looks)."""
    sizes: Counter = Counter()
    for w in top.findChildren(QWidget):
        if not w.isVisible() or w.window() is not top:
            continue
        name = w.objectName()
        sizes[(type(w).__name__, name, w.width(), w.height())] += 1
        tag = f"{place}, {look}: {where(w)}"
        # 1 Every circle is square
        circle = (isinstance(w, QToolButton) and name in ("Circle", "IconBtn")) or name in ("Avatar", "Swatch")
        if circle and w.width() != w.height():
            found.append(f"1 circle not square ({w.width()}×{w.height()}): {tag}")
        # 2 Controls at their token
        inside = isinstance(w.parentWidget(), (QComboBox, QAbstractSpinBox))  # (a dropdown's own text box)
        if isinstance(w, (QPushButton, QLineEdit, QComboBox, QAbstractSpinBox)) and name not in NOT_A_CONTROL:
            want = OWN_HEIGHT.get(name) or tokens.CONTROL_H
            if inside or getattr(top, "search", None) is w:
                continue
            if w.height() != want:
                found.append(f"2 control {w.height()} tall, not {want}: {tag}")
        if name == "Segmented" and w.height() != tokens.CONTROL_H:
            found.append(f"2 segmented track {w.height()} tall: {tag}")
        # 5 Type from the ramp only
        if isinstance(w, (QLabel, QPushButton, QLineEdit, QComboBox)) and (w.text() if hasattr(w, "text") else ""):
            px = QFontInfo(w.font()).pixelSize()
            if px not in RAMP:
                found.append(f"5 type {px}px off the ramp: {tag}")
        # 19 No stray values: a layout's margins and gaps on the grid, or a token
        lay = w.layout()
        if lay is not None and not isinstance(lay, QStackedLayout) and not w.property("measured"):
            m = lay.contentsMargins()
            for v in (m.left(), m.top(), m.right(), m.bottom(), lay.spacing()):
                if v >= 0 and v % 4 and v not in (2, 6, 10, 14) and v not in TOKEN_VALUES and name != "HeadGroup":
                    found.append(f"19 margin or gap {v}: {tag}")
    return sizes


@pytest.fixture
def win(qapp, data_folder, monkeypatch):
    from bodega.ui.window.main_window import MainWindow

    monkeypatch.setenv("BODEGA_REDUCE_MOTION", "1")
    w = MainWindow(sample.fill(Library(data_folder).load()))
    w._restored = True
    w.resize(1280, 900)
    w.show()
    QTest.qWait(50)
    yield w
    w.set_look("dark")
    w.close()


def walk(win, look: str, found: list) -> dict:
    """Every place, a record of each kind, every Settings section and a sheet, measured in `look`."""
    from bodega.ui.dialogs.client import ClientDialog
    from bodega.ui.dialogs.settings import SettingsDialog

    win.set_look(look)
    lib = win.lib
    out = {}
    if win.search.height() != tokens.BAR_CTRL_H:  # 2 the top bar's search is bar-h
        found.append(f"2 the bar's search {win.search.height()} tall, not {tokens.BAR_CTRL_H}: {look}")
    for place in ("gear", "kits", "rentals", "calendar"):
        win.go(place)
        win.deselect()  # (each look starts from the same state: nothing open on the right)
        QTest.qWait(20)
        out[place] = measure(win, place, look, found)
    win.go("gear")
    for kind, obj in (
        ("gear", next(iter(win.gear_table.showing_rows())).data(0, 256)),
        ("packages", next(iter(lib.packages))),
        ("rentals", next(iter(lib.rentals))),
    ):
        win.open(kind, obj)
        QTest.qWait(30)
        out[f"a record ({kind})"] = measure(win, f"a record ({kind})", look, found)
    d = SettingsDialog(lib, win)
    d.show()
    for pane in d.panes:
        d.show_pane(pane)
        QTest.qWait(20)
        out[f"Settings › {pane}"] = measure(d, f"Settings › {pane}", look, found)
    d.done(0)
    c = ClientDialog(next(iter(lib.rentals.values())).client, False, win)
    c.show()
    QTest.qWait(20)
    out["a sheet"] = measure(c, "a sheet", look, found)
    c.done(0)
    return out


def test_g28_measurements_pass_in_light_and_dark_and_sizes_dont_change(win):
    found: list[str] = []
    light = walk(win, "light", found)
    dark = walk(win, "dark", found)
    for place, sizes in light.items():
        if sizes != dark[place]:  # (sizes must not change with the look)
            moved = sorted((sizes - dark[place]) + (dark[place] - sizes))[:6]
            found.append(f"sizes change with the look in {place}: {moved}")
    assert not found, "\n".join(sorted(set(found))[:40])


def test_g28_corners_disabled_toasts_and_motion():
    # 12 Concentric corners: a row's radius is its panel's less the inset
    assert tokens.LIST_ROW_R == tokens.LIST_R - tokens.LIST_INSET  # menu rows 8 in 14 with 6
    assert tokens.NAV_R == tokens.GLASS_R - tokens.NAV_INSET  # sidebar rows in the glass, the inset between
    # 13 Disabled is 40%: every :disabled rule's color is one of the *_OFF colors (made at DISABLED_ALPHA)
    assert tokens.DISABLED_ALPHA == 0.4
    css = theme._sheet()
    off = {getattr(tokens, k) for k in dir(tokens) if k.endswith("_OFF") or k.endswith("_OFF_TEXT")}
    for rule in re.findall(r"[^{}]*:disabled[^{}]*\{([^{}]*)\}", css):
        for color in re.findall(r"(?<![-\w])color:\s*([^;]+);", rule):
            assert color.strip() in off, (rule.strip(), color)
    # 16 Toasts: a success 3.5 s, a warning 6 s, one with Undo 6 to 8 s
    assert (tokens.TOAST_MS, tokens.TOAST_WARN_MS) == (3500, 6000) and 6000 <= tokens.TOAST_UNDO_MS <= 8000


def test_g28_no_motion_under_reduce_motion(monkeypatch):
    # 17 Every animation asks access.duration(): under Reduce Motion it's 0
    monkeypatch.setenv("BODEGA_REDUCE_MOTION", "1")
    names = [k for k in dir(tokens) if k.endswith("_MS") and "SPINNER" not in k and "TOAST" not in k]
    moving = [
        k
        for k in names
        if k in ("DOCK_MS", "FADE_MS", "SEG_SLIDE_MS", "TURN_MS", "SHEET_FADE_MS", "SHEET_RISE_MS", "LIFT_MS")
    ]
    assert moving and all(access.duration(getattr(tokens, k)) == 0 for k in moving)
