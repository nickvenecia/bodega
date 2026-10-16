"""Background work never stops Bodega (the standard's 12.x crash rules): Qt ends the whole app if a thread is
destroyed while it runs, and a window takes its threads with it. A window that goes while its job runs lets the
job go instead: told to stop, kept until it ends, and what it says then goes nowhere."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = r"""
import os, threading, time
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QDialog
app = QApplication([])
from bodega.ui.components import worker
heard, stopped = [], threading.Event()
def job(progress, cancel):
    for _ in range(300):
        if cancel.is_set():
            stopped.set()
            return "stopped"
        time.sleep(0.01)
    return "finished"
d = QDialog()
w = worker.Worker(job, d)
w.done.connect(lambda r: heard.append(r))
w.start()
time.sleep(0.05)
d.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)  # the window goes while its job runs
assert stopped.wait(5), "the job wasn't told to stop"
end = time.monotonic() + 5
while worker._LET_GO and time.monotonic() < end:
    app.processEvents()
    time.sleep(0.01)
app.processEvents()
assert not worker._LET_GO and heard == [], (len(worker._LET_GO), heard)
print("ok")
"""


def test_a_window_that_goes_while_its_job_runs_never_stops_bodega():
    env = {**os.environ, "PYTHONPATH": str(ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    done = subprocess.run([sys.executable, "-c", SCRIPT], capture_output=True, text=True, timeout=60, env=env, cwd=ROOT)
    assert done.returncode == 0 and done.stdout.strip().endswith("ok"), (done.returncode, done.stderr[-2000:])


def test_every_thread_is_a_background():
    """No plain QThread anywhere: each is a components.worker.Background, so none can be destroyed mid-run."""
    plain = []
    for path in (ROOT / "bodega").rglob("*.py"):
        for m in re.finditer(r"^class (\w+)\(QThread\)", path.read_text(encoding="utf-8"), re.M):
            if m.group(1) != "Background":
                plain.append(f"{path.relative_to(ROOT)}: {m.group(1)}")
    assert not plain, plain
