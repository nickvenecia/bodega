"""The window at its smallest (tokens.WINDOW_MIN) and wide, on a screen big enough for both (Qt's test screen is
only 800 wide, so this runs in its own process with a configured one). Nothing in the bar overlaps, the list keeps
room for names, and the open panel stays inside the window."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = r"""
import faulthandler, json, sys, tempfile
faulthandler.enable()  # (a crash says where)
from pathlib import Path
from PySide6.QtCore import qInstallMessageHandler
qInstallMessageHandler(lambda _kind, _where, text: sys.stderr.write(f"Qt: {text}\n"))  # (Windows: else unheard)
from PySide6.QtWidgets import QApplication
from bodega.core.paths import use_data_dir
use_data_dir(Path(tempfile.mkdtemp()) / "data")
app = QApplication(sys.argv[:1])
from bodega.app import setup_app
setup_app(app)
from bodega.core import sample
from bodega.core.store import Library
from bodega.ui.style import tokens
from bodega.ui.window.main_window import MainWindow
from PySide6.QtTest import QTest
out = {}
for name, size in (("smallest", tokens.WINDOW_MIN), ("laptop", (1440, 900)), ("wide", (2200, 1200))):
    w = MainWindow(sample.fill(Library().load()))
    w._restored = True
    w.resize(*size)
    w.show()
    QTest.qWait(200)
    t = w.gear_table
    page = t.parentWidget()
    while page.objectName() != "Center":  # the page between the side panels
        page = page.parentWidget()
    left = t.mapTo(page, t.rect().topLeft()).x()
    edges = [left, page.width() - (left + t.width())]  # the list's two margins, before a panel opens
    it = next(i for i in w.lib.items.values() if not i.parent)
    w.open("gear", it.id)
    QTest.qWait(600)
    def box(x):
        p = x.mapTo(w, x.rect().topLeft())  # where it is in the window
        return [p.x(), p.y(), x.width(), x.height()]
    parts = {k: box(getattr(w, k)) for k in ("title", "search", "view_menu", "btn_export", "btn_new", "btn_ai")}
    t = w.gear_table
    out[name] = {
        "window": [w.width(), w.height()],
        "parts": parts,
        "name_col": t.columnWidth(1),
        "panel": box(w.items),
        "edges": edges,
        "list_w": t.width(),
    }
    w.close()
print(json.dumps(out))
"""


@pytest.fixture(scope="module")
def measured(tmp_path_factory) -> dict:
    folder = tmp_path_factory.mktemp("screen")
    screen = folder / "screen.json"
    screen.write_text(json.dumps({"screens": [{"name": "test", "x": 0, "y": 0, "width": 2560, "height": 1440,
                                               "logicalDpi": 96, "logicalBaseDpi": 96, "dpr": 1}]}), encoding="utf-8")  # fmt: skip
    env = {**os.environ, "QT_QPA_PLATFORM": f"offscreen:configfile={screen}"}
    root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    done = subprocess.run(
        [sys.executable, "-c", SCRIPT], capture_output=True, text=True, timeout=120, env=env, cwd=root
    )
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


def _overlap(a, b) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


@pytest.mark.parametrize("size", ["smallest", "laptop", "wide"])
def test_the_window_fits_at_its_smallest_and_wide(measured, size):
    from bodega.ui.style import tokens

    m = measured[size]
    if size == "smallest":
        assert m["window"] == list(tokens.WINDOW_MIN)
    parts = list(m["parts"].items())
    for n, (a, ra) in enumerate(parts):
        for b, rb in parts[n + 1 :]:
            assert not _overlap(ra, rb), (size, a, b)  # nothing in the bar sits on anything else
    assert m["name_col"] >= tokens.NAME_MIN - 1  # names keep their room; other columns step aside
    x, _y, w, _h = m["panel"]
    assert x >= 0 and x + w <= m["window"][0]  # the open panel is inside the window


@pytest.mark.parametrize("size", ["laptop", "wide"])
def test_the_page_sits_centred_and_stops_at_its_widest(measured, size):
    from bodega.ui.style import tokens

    m = measured[size]
    left, right = m["edges"]
    assert abs(left - right) <= 1  # its two margins match
    assert m["list_w"] <= tokens.PAGE_MAX_W  # never wider than the page's widest
    if size == "wide":  # (2,200 across: the page has stopped growing, and the margins took the rest)
        assert left > tokens.PAGE_INSET
