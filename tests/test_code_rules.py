"""Rules about how the code is written, checked over all of it (so a slip on one platform can't come back)."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "bodega"


def test_every_delayed_call_names_what_it_belongs_to():
    """QTimer.singleShot(ms, owner, fn), never (ms, fn): if the owner is gone first (a window closed and deleted),
    Qt drops the call instead of running it on something that's no longer there. On a Mac the title bar's fit,
    queued as a window showed, once ran after its window was gone and crashed the next window."""
    loose = []
    for p in ROOT.rglob("*.py"):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "singleShot"
                and len(node.args) == 2
            ):
                loose.append(f"{p.relative_to(ROOT)}:{node.lineno}")
    assert loose == [], loose


def test_the_stylesheet_names_no_font_family():
    """Fonts come from theme.font() and the app's own font. A family named in the stylesheet ("inherit" among
    them, which Qt reads as a family called Inherit) makes macOS search every font and warn."""
    text = (ROOT / "ui" / "style" / "theme.py").read_text(encoding="utf-8")
    assert re.findall(r"font-family\s*:", text) == []
