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
        text = f.read_text(encoding="utf-8")
        names |= set(CALLS.findall(text))
    missing = sorted(n for n in names if n not in theme._SVG)
    assert not missing, missing


def test_settings_and_sidebar_icons_exist():
    from bodega.ui.dialogs.settings import PANES

    names = {icon for _k, _l, icon in PANES} | set(
        ROWS.findall((ROOT / "ui/window/sidebar.py").read_text(encoding="utf-8"))
    )
    assert names and all(n in theme._SVG for n in names), names


def test_the_app_icon_is_drawn_from_its_one_vector_source(qapp):
    """V-41: bodega/assets/icon.png is icon.svg as scripts/make_icon.py draws it (the build makes every other size
    from the PNG), so a change to one without the other fails here."""
    import importlib.util

    from PySide6.QtGui import QImage

    spec = importlib.util.spec_from_file_location("make_icon", ROOT.parent / "scripts" / "make_icon.py")
    make_icon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(make_icon)
    drawn = make_icon.draw()
    kept = QImage(str(make_icon.PNG)).convertToFormat(drawn.format())

    def apart(a, b) -> int:
        return max(
            abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue()), abs(a.alpha() - b.alpha())
        )

    far = sum(
        apart(drawn.pixelColor(x, y), kept.pixelColor(x, y)) > 64 for x in range(0, 1024, 4) for y in range(0, 1024, 4)
    )
    assert make_icon.SVG.exists() and far < 20, far  # (the same picture)
