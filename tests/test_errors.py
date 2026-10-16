"""What went wrong, said plainly: the computer's errors never reach a person as "[Errno 13] Permission denied"."""

import errno
import socket
import urllib.error

import pytest

from bodega.core import errors
from bodega.services.ai.providers import AIError


@pytest.mark.parametrize(
    "code, words",
    [
        (errno.ENOSPC, "no free space"),
        (errno.EACCES, "isn't allowed to write"),
        (errno.EPERM, "isn't allowed to write"),
        (errno.EROFS, "only be read"),
        (errno.ENOENT, "isn't there any more"),
        (errno.EBUSY, "another app has the file open"),
        (errno.ENAMETOOLONG, "too long"),
    ],
)
def test_the_computers_errors_in_plain_words(code, words):
    said = errors.plain(OSError(code, "raw words from the system", "/a/path"), "save the PDF")
    assert said.startswith("Couldn't save the PDF: ") and words in said
    assert "Errno" not in said and "raw words" not in said and "/a/path" not in said
    assert said.endswith(".")


def test_windows_codes_are_read_too():
    e = OSError(errno.EINVAL, "The process cannot access the file")
    e.winerror = 32  # another program has it open
    assert "another app has the file open" in errors.plain(e, "save the backup")


def test_the_internets_errors_never_show_their_raw_text():
    gone = urllib.error.URLError(socket.gaierror(-2, "Name or service not known"))
    assert errors.plain(gone, "check for updates") == (
        "Couldn't check for updates: Bodega couldn't reach the internet. Check your connection, then try again."
    )
    page = urllib.error.HTTPError("https://example.com", 503, "Service Unavailable", {}, None)
    assert "didn't answer properly" in errors.plain(page, "check the price")
    assert "timed out" not in errors.plain(TimeoutError("timed out"), "check the price")


def test_bodegas_own_plain_words_pass_through():
    assert errors.plain(AIError("The key wasn't accepted."), "ask") == "The key wasn't accepted."
    assert errors.plain(OSError("That page isn't on B&H any more."), "x") == "That page isn't on B&H any more."


def test_anything_unknown_gets_a_reference_that_matches_the_log(caplog):
    said = errors.plain(RuntimeError("internal detail"), "finish that")
    assert "internal detail" not in said and "send feedback with ref " in said
    ref = said.rsplit("ref ", 1)[1].rstrip(".")
    assert len(ref) == 4 and any(f"ref {ref}" in r.getMessage() for r in caplog.records)


def test_number_fields_take_only_what_they_can_read(qapp):
    """A letter in an amount, a percent or a day count is refused as it's typed, never read as 0 later."""
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLineEdit

    from bodega.ui.components.widgets import WHOLE_TYPED, MoneyField, only, percent_field

    cases = [
        (MoneyField(), "abc$1,5x00.505", "$1,500.50"),
        (percent_field(), "8.8a75%", "8.875%"),
        (percent_field(), "-15", "15"),
        (only(QLineEdit(), WHOLE_TYPED), "3 days", "3"),
    ]
    for field, typed, kept in cases:
        QTest.keyClicks(field, typed)
        assert field.text().strip() == kept, (typed, field.text())
        field.deleteLater()


def test_an_error_nobody_expected_is_said_in_the_window(qapp, data_folder, monkeypatch, caplog):
    import sys

    from PySide6.QtWidgets import QApplication

    from bodega import app as app_module
    from bodega.core import sample
    from bodega.core.store import Library
    from bodega.ui.window.main_window import MainWindow

    win = MainWindow(sample.fill(Library(data_folder).load()))
    win.show()
    said = []
    monkeypatch.setattr(win, "toast", lambda text, tone="": said.append((text, tone)))
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)  # put back afterwards
    monkeypatch.setattr("threading.excepthook", __import__("threading").excepthook)
    app_module._log_uncaught()
    monkeypatch.setattr(sys, "__excepthook__", lambda *_a: None)
    try:
        raise RuntimeError("deep inside Qt")
    except RuntimeError:
        sys.excepthook(*sys.exc_info())
    QApplication.processEvents()
    assert said and said[0][1] == "problem" and "deep inside" not in said[0][0]
    ref = said[0][0].rsplit("ref ", 1)[1].rstrip(".")
    assert any(f"ref {ref}" in r.getMessage() for r in caplog.records)  # the same reference as the log
    win.close()
