"""Every icon the code names exists (a missing one only shows up as a crash when its button is drawn)."""

from __future__ import annotations

import re
from pathlib import Path

from bodega.ui.style import theme

ROOT = Path(__file__).resolve().parent.parent / "bodega"
CALLS = re.compile(r'(?:icon|menu_icon|IconLabel|circle_button|icon_button|header_icon|set_icon)\(\s*"([a-z0-9-]+)"')
ROWS = re.compile(r'_row\(\s*"[^"]+",\s*"[^"]+",\s*"([a-z0-9-]+)"')  # a sidebar row: key, label, icon


def test_every_named_icon_exists():
    names = set()
    for f in ROOT.rglob("*.py"):
        text = f.read_text()
        names |= set(CALLS.findall(text))
    missing = sorted(n for n in names if n not in theme._SVG)
    assert not missing, missing


def test_settings_and_sidebar_icons_exist():
    from bodega.ui.dialogs.settings import PANES

    names = {icon for _k, _l, icon in PANES} | set(ROWS.findall((ROOT / "ui/window/sidebar.py").read_text()))
    assert names and all(n in theme._SVG for n in names), names
