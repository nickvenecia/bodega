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


# A private name a UI test still reaches, and why it can't do it as a person would: "file:name" -> the reason.
# Keep it short: anything else a UI test needs it finds by its words or its role (tests/ui.py), or the part makes
# it public (an object name for by_id, or a method the app itself has).
PRIVATE_ALLOWED = {
    "ui.py:_restored": "The window opens where it was left and saves its size and place for next time; a test or a "
    "screenshot needs it at a size it sets instead. A person never wants that, so the window has no setting for it "
    "and keeps it as a private note: tests/ui.py's keep_size() is the one place a test sets it.",
    "test_window.py:_done": "When every row of a sheet is gear you already have, Import is off even with Add Links "
    "to Pieces You Have on, so no click reaches the links choice (a person can't bring only links in yet: a bug "
    "to fix in the Import window). The test finishes the window the way Import would.",
}


def _imported(tree: ast.AST) -> dict[str, set[str]]:
    """Each name a file imports (anywhere in it) with what it is: "bodega.ui.style.tokens", "os"…"""
    names: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.setdefault(a.asname or a.name.split(".")[0], set()).add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            for a in node.names:
                names.setdefault(a.asname or a.name, set()).add(f"{node.module}.{a.name}")
    return names


def _root(node: ast.AST) -> str:
    """The name an expression starts from (`win` in `win.items.name.text()`), or "" for anything else."""
    while isinstance(node, (ast.Attribute, ast.Call, ast.Subscript)):
        node = node.func if isinstance(node, ast.Call) else node.value
    return node.id if isinstance(node, ast.Name) else ""


def _ui_parts(tree: ast.Module, window_fixtures: set[str]) -> list[ast.AST]:
    """What in a test file builds a window or dialog: its tests and fixtures that take `qapp` (or a fixture that
    does) and, once it has any, the helpers they use (everything else at the top of the file)."""
    tops = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
    funcs = [n for n in tops if isinstance(n, ast.FunctionDef)]

    def is_fixture(f: ast.FunctionDef) -> bool:
        return any("fixture" in ast.unparse(d) for d in f.decorator_list)

    def takes_a_window(f: ast.FunctionDef) -> bool:
        return any(a.arg in window_fixtures for a in f.args.args)

    for _ in funcs:  # (a fixture can take one that takes qapp)
        window_fixtures |= {f.name for f in funcs if is_fixture(f) and takes_a_window(f)}
    ui = [f for f in funcs if (f.name.startswith("test_") or is_fixture(f)) and takes_a_window(f)]
    if not ui:
        return []
    return ui + [
        n for n in tops if not (isinstance(n, ast.FunctionDef) and (n.name.startswith("test_") or is_fixture(n)))
    ]


def test_ui_tests_never_reach_a_parts_private_names():
    """The standard's T-13 and T-04: a UI test finds what it works with as a person does (a button by its words, a
    field by its label, a menu command by its menu and its words: tests/ui.py) or by the part's own object name,
    and acts through what the part makes public, never through a `._name`. A test that reaches a part's private
    name breaks when the part is tidied though a person sees nothing change, and it can pass doing what a person
    couldn't (a click on a button that's off). A UI test builds a window or dialog: it takes `qapp`, or a fixture
    that does. What it reaches through a name it imported from outside bodega/ui (bodega.core, the standard
    library, Qt) is a unit test's business and isn't counted; anything else is, unless PRIVATE_ALLOWED says why."""
    tests = ROOT.parent / "tests"
    conftest = ast.parse((tests / "conftest.py").read_text(encoding="utf-8"))
    window_fixtures = {"qapp"} | {
        f.name for f in conftest.body if isinstance(f, ast.FunctionDef) and any(a.arg == "qapp" for a in f.args.args)
    }
    found, used = [], set()
    for p in sorted(tests.glob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        parts = [tree] if p.name == "ui.py" else _ui_parts(tree, set(window_fixtures))
        outside = {n for n, what in _imported(tree).items() if not any(w.startswith("bodega.ui") for w in what)}
        for part in parts:
            known = set(outside)
            made = [n for n in ast.walk(part) if isinstance(n, ast.Assign) and len(n.targets) == 1]
            for _ in made:  # names made from something outside bodega/ui (`pace = tasks.Pace()`)
                known |= {
                    a.targets[0].id for a in made if isinstance(a.targets[0], ast.Name) and _root(a.value) in known
                }
            for node in ast.walk(part):
                private = (
                    isinstance(node, ast.Attribute) and node.attr.startswith("_") and not node.attr.startswith("__")
                )
                if not private or _root(node.value) in known:
                    continue
                key = f"{p.name}:{node.attr}"
                if key in PRIVATE_ALLOWED:
                    used.add(key)
                else:
                    found.append(f"{p.name}:{node.lineno}: {ast.unparse(node)}")
    assert found == [], "\n".join(sorted(set(found)))
    assert set(PRIVATE_ALLOWED) <= used, f"no longer reached, so off the list: {set(PRIVATE_ALLOWED) - used}"
