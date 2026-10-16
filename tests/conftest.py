"""Shared test setup: an offscreen Qt app and a throwaway data folder for every test.

A warning from Qt fails the test it came in (unless the test is marked qt_warnings: it feeds Qt a broken file
on purpose). The offscreen screen's own limits ("This plugin does not support raise()") aren't warnings about
Bodega and are let through.

Qt objects made during the UI tests can crash while Python tears itself down after the last test,
turning a green run red in CI. Once every test has finished, leave with pytest's own result.
"""

from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_status: dict = {"code": 0}
QT_NOISE = ("This plugin does not support",)  # the offscreen screen has no window manager to ask
_qt_said: list[str] = []


def _qt_message(kind, _context, message: str) -> None:
    from PySide6.QtCore import QtMsgType

    bad = kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg)
    if bad and not message.startswith(QT_NOISE):
        _qt_said.append(message)
        sys.stderr.write(f"Qt: {message}\n")


def pytest_configure(config):
    from PySide6.QtCore import qInstallMessageHandler

    qInstallMessageHandler(_qt_message)
    _status["config"] = config


def pytest_runtest_logreport(report):
    """A failure is written out as it happens, not only in the summary at the end: if Qt crashes later in the run
    (it can, on a Mac or on Windows), the log still says what failed and why."""
    if not report.failed:
        return
    tr = _status["config"].pluginmanager.get_plugin("terminalreporter")
    if tr is not None:
        tr.write_line(f"\n--- FAILED {report.nodeid} ({report.when}) ---")
        tr.write_line(report.longreprtext[-4000:])
        for name, text in report.sections:  # what it printed, Qt's own messages among them
            if "stderr" in name or "stdout" in name:
                tr.write_line(f"[{name}] {text[-1500:]}")


def pytest_sessionfinish(session, exitstatus):
    _status["code"] = int(exitstatus)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    if "PySide6.QtWidgets" in sys.modules:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(_status["code"])


@pytest.fixture(autouse=True)
def fresh_ai_meter():
    """Every test starts with nothing asked of the AI today, and no per-minute wait (fake providers answer at
    once; tests/test_ai.py checks the limits with a meter of their own)."""
    from bodega.services.ai import usage

    usage.METER = usage.Meter(rate=10**6)
    yield


@pytest.fixture(autouse=True)
def data_folder(tmp_path):
    """Never touch the real gear: every test gets its own empty data folder."""
    from bodega.core.paths import use_data_dir

    use_data_dir(tmp_path / "data")
    yield tmp_path / "data"
    use_data_dir(None)


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])
    from bodega.app import setup_app

    setup_app(app)
    return app


@pytest.fixture(autouse=True)
def _no_leftover_windows():
    """Windows a test made are gone before the next one (otherwise every later restyle redoes them all)."""
    yield
    if "PySide6.QtWidgets" not in sys.modules:
        return
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return
    for w in app.topLevelWidgets():
        w.close()
        w.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture(autouse=True)
def _qt_stays_quiet(request):
    """Qt said nothing was wrong during the test."""
    _qt_said.clear()
    yield
    said, _qt_said[:] = list(_qt_said), []
    if said and request.node.get_closest_marker("qt_warnings") is None:
        pytest.fail("Qt warned: " + " | ".join(said[:5]))
