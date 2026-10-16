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


def test_no_action_made_by_qt_is_kept():
    """An action that's kept (`self.act_up = …`, `self.acts[k] = …`) is made by widgets.menu_item, never by
    `menu.addAction(text…)`: Python hears when Qt deletes an action it made itself, never one Qt made. Kept, that
    one outlived its action when a rental's lines were rebuilt, and the next object Qt made at the same address
    crashed the Intel Mac (and turned a menu's action into a layout item on Linux)."""
    kept = []
    for p in ROOT.rglob("*.py"):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            f = node.value.func
            made_by_qt = isinstance(f, ast.Attribute) and f.attr == "addAction" and node.value.args
            on_self = any(
                isinstance(t, (ast.Attribute, ast.Subscript)) and "self" in ast.unparse(t) for t in node.targets
            )
            if made_by_qt and on_self:
                kept.append(f"{p.relative_to(ROOT)}:{node.lineno}")
    assert kept == [], kept


def test_every_text_file_is_read_and_written_as_utf8():
    """`read_text`, `write_text` and `open(…)` for text always say `encoding="utf-8"`: without it Windows uses its own
    code page, and a curly quote in a file stopped a test there (the tests and scripts are checked too)."""
    loose = []
    for where in (ROOT, ROOT.parent / "tests", ROOT.parent / "scripts"):
        for p in where.rglob("*.py"):
            for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                if not isinstance(node, ast.Call) or any(k.arg == "encoding" for k in node.keywords):
                    continue
                f = node.func
                name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
                if name in ("read_text", "write_text") and isinstance(f, ast.Attribute):
                    loose.append(f"{p.relative_to(ROOT.parent).as_posix()}:{node.lineno}")
                elif name == "open" and isinstance(f, ast.Name):
                    mode = (
                        node.args[1]
                        if len(node.args) > 1
                        else next((k.value for k in node.keywords if k.arg == "mode"), None)
                    )
                    text = not (isinstance(mode, ast.Constant) and "b" in str(mode.value))
                    if text:
                        loose.append(f"{p.relative_to(ROOT.parent).as_posix()}:{node.lineno}")
    assert loose == [], loose


def test_no_layout_is_asked_for_its_items():
    """A layout's widgets come from widgets.widgets_of, never `layout.itemAt(n)`: PySide keeps the stand-in for an
    item it was asked for as long as the layout lives, and when Qt throws the item away (a rental's lines rebuilt)
    the next object made at its address meets it. That crashed CI on the Intel Mac, the Apple Mac and Linux.
    (A list's own itemAt(point), in tables.py, gives its rows, which are Bodega's.)"""
    asked = []
    for where in (ROOT, ROOT.parent / "tests"):
        for p in where.rglob("*.py"):
            if p.name == "tables.py":
                continue
            for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "itemAt":
                    asked.append(f"{p.relative_to(ROOT.parent).as_posix()}:{node.lineno}")
    assert asked == [], asked
