"""The accent color you pick: every choice gets a full, readable set of shades; the choice is kept."""

from __future__ import annotations

import colorsys
import re

from bodega.core import sample
from bodega.core.store import Library, read_json
from bodega.ui.style import tokens

COLOR = re.compile(r"^(#[0-9A-F]{6}|rgba\(\d+, \d+, \d+, [0-9.]+\))$")


def test_every_choice_has_every_shade_and_reads():
    keys = {k for k in tokens.DARK if k.startswith(("ACCENT", "CHIP")) or k == "ON_ACCENT"}
    for name, dark, light in tokens.ACCENTS.values():
        for base, scheme in ((dark, "dark"), (light, "light")):
            shades = tokens.accent_set(base, scheme)
            canvas = (tokens.LIGHT if scheme == "light" else tokens.DARK)["BG"]
            assert keys <= set(shades), name
            assert all(COLOR.match(v) for v in shades.values()), name
            # words: white on the fill, and the accent as words on the page, at 4.5:1 (the standard's A.1)
            assert tokens.contrast(shades["ON_ACCENT"], shades["ACCENT_FILL"]) >= 4.5, (name, scheme)
            assert tokens.contrast(shades["ACCENT_TEXT"], canvas) >= 4.5, (name, scheme)


def test_bodegas_own_blue_reads_too():
    for look in (tokens.DARK, tokens.LIGHT):
        assert tokens.contrast(look["ON_ACCENT"], look["ACCENT_FILL"]) >= 4.5
        assert tokens.contrast(look["ACCENT_TEXT"], look["BG"]) >= 4.5
        assert tokens.contrast(look["MUTED"], look["BG"]) >= 4.5  # secondary words are information
        assert tokens.contrast("#FFFFFF", look["BAD_BUTTON"]) >= 4.5
        for meaning in ("GOOD", "BAD", "WARN", "INFO"):
            assert tokens.contrast(look[meaning], look["BG"]) >= 4.5, meaning
        glass = tokens._solid(look["GLASS"], look["BG"])  # the sidebar's counts and labels sit on the glass
        assert tokens.contrast(look["MUTED"], glass) >= 4.5


def test_the_accent_is_kept_for_what_you_can_press():
    """Statuses and counts take their meaning's color (Booked is info blue), never the accent."""
    from bodega.ui.window.calendar_view import BAR_TONES
    from bodega.ui.window.tables import STATUS_COLORS

    assert "ACCENT" not in STATUS_COLORS.values()
    assert not any(c.startswith("ACCENT") or c == "ON_ACCENT" for tone in BAR_TONES.values() for c in tone)
    assert STATUS_COLORS["booked"] == "INFO" and "FAINT" not in STATUS_COLORS.values()


def test_no_accent_is_red_since_red_means_late_failed_or_delete():
    for _name, dark, light in tokens.ACCENTS.values():
        for c in (dark, light):
            h, _l, sat = colorsys.rgb_to_hls(*(v / 255 for v in tokens._rgb(c)))
            assert sat < 0.25 or 18 <= h * 360 <= 340, c  # red means late, failed or delete


def test_use_switches_and_comes_back():
    try:
        tokens.use("dark", "green")
        assert tokens.ACCENTS["green"][1] == tokens.ACCENT and tokens.ON_ACCENT == "#FFFFFF"
        assert tokens.contrast(tokens.ON_ACCENT, tokens.ACCENT_FILL) >= 4.5
        tokens.use("light")  # keeps the accent
        assert tokens.ACCENTS["green"][2] == tokens.ACCENT
        tokens.use("dark", "")  # Bodega's own: the hand-set shades, exactly
        assert tokens.DARK["ACCENT"] == tokens.ACCENT and tokens.DARK["DIVIDER"] == tokens.DIVIDER
        tokens.use("dark", "no-such-color")
        assert tokens.ACCENT_KEY == tokens.APP_ACCENT
    finally:
        tokens.use("dark", "")


def test_picking_an_accent_in_settings(qapp, data_folder):
    from bodega.app import set_appearance
    from bodega.ui.dialogs.settings import SettingsDialog
    from bodega.ui.window.main_window import MainWindow

    win = MainWindow(sample.fill(Library(data_folder).load()))
    win.show()
    set_appearance(qapp, "dark", "")  # whatever look an earlier test left on
    try:
        d = SettingsDialog(win.lib, win, "general")
        assert d.accent.current == tokens.APP_ACCENT
        d.accent._pick("purple")
        assert tokens.ACCENTS["purple"][1] == tokens.ACCENT
        assert tokens.ACCENTS["purple"][1] in qapp.styleSheet()
        assert read_json(data_folder / "settings.json", {}).get("accent") == "purple"
        d.accent._pick(tokens.APP_ACCENT)
        assert read_json(data_folder / "settings.json", {}).get("accent") == ""
        assert tokens.DARK["ACCENT"] == tokens.ACCENT
        d.close()
    finally:
        set_appearance(qapp, "dark", "")
        win.close()


def test_anything_off_is_drawn_at_forty_percent_in_every_look():
    from pathlib import Path

    try:
        for scheme in ("dark", "light"):
            for key in tokens.ACCENTS:
                tokens.use(scheme, key)
                assert tokens.faded(tokens.ACCENT_FILL) == tokens.ACCENT_OFF
                assert tokens.faded(tokens.TEXT) == tokens.TEXT_OFF
                assert all(COLOR.match(getattr(tokens, k)) for k in ("TEXT_OFF", "FILL_OFF", "ACCENT_OFF_TEXT"))
        assert tokens.faded("rgba(120, 120, 128, 0.5)") == "rgba(120, 120, 128, 0.2)"
    finally:
        tokens.use("dark", tokens.APP_ACCENT)
    qss = (Path(__file__).resolve().parents[1] / "bodega" / "ui" / "style" / "theme.py").read_text(encoding="utf-8")
    off = [ln for ln in qss.splitlines() if ":disabled" in ln and "color:" in ln and "transparent" not in ln]
    assert off and all("_OFF}" in ln for ln in off), off  # one rule: never a hand-picked grey


def test_the_accent_you_picked_comes_back_next_time(qapp, data_folder):
    from bodega.app import saved_look
    from bodega.core.store import write_json

    data_folder.mkdir(parents=True, exist_ok=True)
    write_json(data_folder / "settings.json", {"appearance": "light", "accent": "purple"})
    assert saved_look() == ("light", "purple")  # what Bodega opens with
    write_json(data_folder / "settings.json", {"appearance": 3, "accent": None})
    assert saved_look() == ("system", "")  # an odd file: the defaults


def test_the_light_looks_whites_and_greys_lean_toward_the_accent():
    """(The standard's 2.3, V-26) Each neutral keeps its lightness and takes a little of the accent's hue: pink gives
    warm whites, blue cool ones, graphite plain greys. Words that mean something never lean, nor does the dark look,
    and every pairing still reads."""
    import math

    try:
        for key, (name, _dark, light) in tokens.ACCENTS.items():
            tokens.use("light", key)
            for k in tokens.TINT:
                was, now = tokens.LIGHT[k], getattr(tokens, k)
                solid = lambda c: tokens._hex(float(x) for x in c[5:-1].split(",")[:3]) if c.startswith("rgba") else c
                L0, a0, b0 = tokens.oklab(solid(was))
                L1, a1, b1 = tokens.oklab(solid(now))
                assert L1 <= L0 + 0.002 and L0 - L1 < 0.02, (name, k)  # its lightness, near enough (white gives a hair)
                _l, aa, ab = tokens.oklab(light)
                if math.hypot(aa, ab) > 0.05:  # a colorful accent: it leans its way
                    assert math.hypot(a1 - aa, b1 - ab) < math.hypot(a0 - aa, b0 - ab), (name, k)
            if key == "graphite":  # (as numbers: "0.90" and "0.9" are one see-through)
                same = lambda a, b: tokens._solid(a, "#FFFFFF") == tokens._solid(b, "#FFFFFF")
                assert all(same(getattr(tokens, k), tokens.LIGHT[k]) for k in ("BG", "PANEL", "GLASS", "MUTED")), name
            for meaning in ("GOOD", "BAD", "WARN", "INFO", "PAPER"):
                assert getattr(tokens, meaning) == tokens.LIGHT[meaning], (name, meaning)
            assert tokens.contrast(tokens.MUTED, tokens.BG) >= 4.5, name
            assert tokens.contrast(tokens.MUTED, tokens._solid(tokens.GLASS, tokens.BG)) >= 4.5, name
            assert tokens.contrast(tokens.TEXT, tokens.PANEL) >= 4.5, name
            assert tokens.contrast(tokens.ACCENT_TEXT, tokens.BG) >= 4.5, name
            for meaning in ("GOOD", "BAD", "WARN", "INFO"):
                assert tokens.contrast(getattr(tokens, meaning), tokens.BG) >= 4.5, (name, meaning)
            tokens.use("dark", key)
            assert all(getattr(tokens, k) == tokens.DARK[k] for k in ("BG", "PANEL", "GLASS", "MUTED")), name
    finally:
        tokens.use("dark", tokens.APP_ACCENT)
