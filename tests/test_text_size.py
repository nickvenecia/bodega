"""Larger text (the standard's V-16, A-07, §7.5): Bodega draws at the text size you choose (Settings › General) or the
computer's own, up to 200%, the whole window growing with it. At 200% nothing is cut short or overlaps: on a large
screen everything fits as it is; on a smaller one the window fits the screen and the layout gives way (the sidebar
folds behind a button, figures and totals that don't fit step aside). Run at Qt's scale in its own process, on a
configured screen."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = r"""
import json, sys, tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication
from bodega.core.paths import use_data_dir
use_data_dir(Path(tempfile.mkdtemp()) / "data")
app = QApplication(sys.argv[:1])
from bodega.app import setup_app
setup_app(app)
from bodega.core import sample
from bodega.core.store import Library
from bodega.ui.window.main_window import MainWindow
from PySide6.QtTest import QTest
w = MainWindow(sample.fill(Library().load()))
w._restored = True
w.resize(w.minimumSize())
w.show()
QTest.qWait(300)
it = next(i for i in w.lib.items.values() if not i.parent)
w.open("gear", it.id)
QTest.qWait(600)
def box(x):
    p = x.mapTo(w, x.rect().topLeft())
    return [p.x(), p.y(), x.width(), x.height()]
bar = {k: box(getattr(w, k)) for k in ("btn_sidebar", "title", "search", "view_menu", "btn_export", "btn_new", "btn_ai")
       if getattr(w, k).isVisible()}
cut = []
for t in w.figure_row.tiles:
    if t.isVisible():
        cut += [l.text() for l in t.findChildren(type(w.title)) if l.isVisible() and l.width() < l.sizeHint().width()]
for key, cell in w.total_cells.items():
    if cell.isVisible():
        cut += [l.text() for l in cell.findChildren(type(w.title)) if l.width() < l.sizeHint().width()]
if w.title.width() < w.title.sizeHint().width():
    cut.append(w.title.text())
print(json.dumps({
    "scale": w.devicePixelRatioF(),
    "window": [w.width(), w.height()],
    "screen": [w.screen().availableGeometry().width(), w.screen().availableGeometry().height()],
    "sidebar": w.sidebar.isVisible(),
    "bar": bar,
    "cut": cut,
    "name_col": w.gear_table.columnWidth(1),
    "panel": box(w.items),
}))
"""


def run_at(tmp_path_factory, width: int, height: int, scale: str) -> dict:
    folder = tmp_path_factory.mktemp("screen")
    (folder / "screen.json").write_text(
        json.dumps({"screens": [{"name": "test", "x": 0, "y": 0, "width": width, "height": height,
                                 "logicalDpi": 96, "logicalBaseDpi": 96, "dpr": 1}]}),
        encoding="utf-8",
    )  # fmt: skip
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen:configfile=screen.json", "QT_SCALE_FACTOR": scale}
    root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    done = subprocess.run(
        [sys.executable, "-c", SCRIPT], capture_output=True, text=True, timeout=120, env=env, cwd=folder
    )
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


def _overlap(a, b) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


@pytest.mark.parametrize(("screen", "sidebar"), [((2560, 1440), True), ((1920, 1080), False)], ids=["large", "1080p"])
def test_at_200_percent_nothing_is_cut_or_overlaps(tmp_path_factory, screen, sidebar):
    from bodega.ui.style import tokens

    m = run_at(tmp_path_factory, *screen, "2")
    assert m["scale"] == 2.0
    assert m["window"][0] <= m["screen"][0] and m["window"][1] <= m["screen"][1]  # the window fits the screen
    assert m["sidebar"] is sidebar  # (folded away only where the window is narrow)
    parts = list(m["bar"].items())
    for n, (a, ra) in enumerate(parts):
        for b, rb in parts[n + 1 :]:
            assert not _overlap(ra, rb), (a, b)
    assert not m["cut"], m["cut"]  # no figure, total or title cut short
    assert m["name_col"] >= tokens.NAME_MIN  # names keep their room
    x, _y, w, _h = m["panel"]
    assert x + w <= m["window"][0]


def test_the_text_size_is_yours_or_the_computers(monkeypatch):
    from bodega.ui.components import access

    monkeypatch.setenv("BODEGA_TEXT_SCALE", "1.5")
    assert access.text_scale(0) == 1.5  # Match System
    assert access.text_scale(125) == 1.25 and access.text_scale(200) == 2.0
    assert access.text_scale(999) == 1.5  # (a number Bodega doesn't offer: the system's)
    monkeypatch.setenv("BODEGA_TEXT_SCALE", "3")
    assert access.text_scale(0) == 2.0  # never past 200%


def test_the_chosen_size_is_drawn_from_the_next_start(data_folder, monkeypatch):
    import json as js

    from bodega import app

    data_folder.mkdir(parents=True, exist_ok=True)
    (data_folder / "settings.json").write_text(js.dumps({"text_size": 150}), encoding="utf-8")
    monkeypatch.delenv("QT_SCALE_FACTOR", raising=False)
    assert app.use_text_size() == 1.5 and os.environ["QT_SCALE_FACTOR"] == "1.5"
    monkeypatch.setenv("QT_SCALE_FACTOR", "1.25")  # one already asked for is kept
    app.use_text_size()
    assert os.environ["QT_SCALE_FACTOR"] == "1.25"


def test_settings_keeps_the_text_size_and_offers_a_restart(qapp, data_folder, monkeypatch):
    from bodega.core import sample
    from bodega.core.store import Library
    from bodega.ui.dialogs.settings import SettingsDialog
    from bodega.ui.window.main_window import MainWindow

    monkeypatch.delenv("QT_SCALE_FACTOR", raising=False)
    monkeypatch.setenv("BODEGA_TEXT_SCALE", "1")
    w = MainWindow(sample.fill(Library(data_folder).load()))
    d = SettingsDialog(w.lib, w, "general")
    assert d.restart.parentWidget().isHidden()  # the size you see is the one picked
    d.text_size.setCurrentIndex(d.text_size.findData("150"))
    assert w.lib.settings["text_size"] == 150 and not d.restart.parentWidget().isHidden()
    d.close()
    w.close()


def test_a_narrow_window_folds_the_sidebar_and_brings_it_back(qapp, data_folder):
    from bodega.core import sample
    from bodega.core.store import Library
    from bodega.ui.style import tokens
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(sample.fill(Library(data_folder).load()))
    w.setMinimumSize(0, 0)
    w.resize(tokens.NARROW_W - 100, 600)
    w.show()
    qapp.processEvents()
    assert w.sidebar.isHidden() and w.btn_sidebar.isVisible() and w.sidebar_act.text() == "Show Sidebar"
    w.btn_sidebar.click()  # shown, by you: it stays
    assert not w.sidebar.isHidden() and w.sidebar_act.text() == "Hide Sidebar"
    w.resize(tokens.NARROW_W - 50, 600)
    qapp.processEvents()
    assert not w.sidebar.isHidden()
    w.sidebar_act.trigger()
    assert w.sidebar.isHidden()
    w.close()
