"""Words are never cut off: every screen, at the window's usual size and its smallest, checked by tests/cut_off.py.

Fonts are wider on some computers (a Mac's run wider than Linux's), so every screen is also checked with its
letters spaced 10% wider: text that only just fits here would be cut off there.
A new screen (a place, a panel, a dialog, a Settings section) gets a line here.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QDialog, QLabel, QPushButton

from bodega.core import pricing, sample
from bodega.core.store import Library
from bodega.ui.style import tokens
from tests.cut_off import cut_off

SIZES = pytest.mark.parametrize("size", [tokens.WINDOW_SIZE, tokens.WINDOW_MIN], ids=["usual", "smallest"])
WIDER = 110  # the wider check: letters spaced 10% wider (% of their usual spacing)


@pytest.fixture(params=[100, WIDER], ids=["as-here", "wider"])
def letters(request, qapp):
    """The app's letters as they are here, or spaced wider (as a computer with wider fonts draws them)."""
    from PySide6.QtGui import QFont

    was = QFont(qapp.font())
    f = QFont(was)
    f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, request.param)
    qapp.setFont(f)
    yield request.param
    qapp.setFont(was)


def settle() -> None:
    """Let what slides or fades in get to where it stops."""
    from PySide6.QtTest import QTest

    QTest.qWait(max(tokens.DOCK_MS, tokens.FADE_MS, tokens.TOAST_IN_MS) + 100)


def look(w, where: str, found: list[str]) -> None:
    settle()
    found += [f"{where}: {x}" for x in cut_off(w)]


def window(lib: Library, size: tuple[int, int]):
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(lib)
    w._restored = True  # this size, not the screen's
    w.resize(*size)
    w.show()
    return w


def test_the_checker_finds_cut_off_words(qapp):
    words = "A long sentence that will never fit in sixty pixels"
    label, button = QLabel(words), QPushButton(words)
    for w in (label, button):
        w.setFixedWidth(60)
        w.show()
        assert len(cut_off(w)) == 1, w
    label.setWordWrap(True)
    label.setFixedHeight(label.heightForWidth(60))
    assert cut_off(label) == []


@SIZES
def test_first_launch(qapp, data_folder, letters, size):
    found: list[str] = []
    w = window(Library(data_folder).load(), size)
    for place in ("gear", "kits", "rentals", "upcoming", "calendar"):
        w.go(place)
        look(w, place, found)
    w.close()
    assert found == [], "\n" + "\n".join(found)


@SIZES
def test_every_place_and_panel(qapp, data_folder, letters, size):
    found: list[str] = []
    lib = sample.fill(Library(data_folder).load())
    w = window(lib, size)
    look(w, "gear", found)
    top = next(i for i in lib.ordered_items() if pricing.children(lib, i.id))
    w.gear_table.opened.add(top.id)
    w.refresh()
    w.open("gear", top.id)
    look(w, "a piece of gear", found)
    w.set_gear_filter("out")
    look(w, "gear, filtered", found)
    w.set_gear_filter("all")
    w.go(f"grp:{lib.groups()[0]}")
    look(w, "a group", found)
    w.go("kits")
    look(w, "kits", found)
    w.open("packages", next(iter(lib.packages)))
    look(w, "a kit", found)
    w.go("rentals")
    look(w, "rentals", found)
    w.open("rentals", next(iter(lib.rentals)))
    for e in w.rentals.editors:
        w.rentals._open_editor(e)
    look(w, "a rental, every line open", found)
    for place in ("out", "upcoming", "calendar"):
        w.go(place)
        look(w, place, found)
    w.calendar.set_mode("timeline")
    look(w, "timeline", found)
    w.calendar.set_mode("month")
    w.go("gear")
    w.open_ai_assistant()
    w.assistant.say(
        "Bodega", "Ask about your gear, or pick a job: Update from Links, Find Links, Tidy Names."
    )
    look(w, "the assistant", found)
    w.close_assistant()
    w.close()
    assert found == [], "\n" + "\n".join(found)


def test_every_dialog(qapp, data_folder, letters, tmp_path, monkeypatch):
    """Each window the app opens, through the command that opens it (shown, checked, then closed)."""
    import openpyxl

    from bodega import __version__
    from bodega.core import update
    from bodega.services.ai.tasks import Change, Result
    from bodega.ui.dialogs import common
    from bodega.ui.dialogs.account import SignInDialog
    from bodega.ui.dialogs.ai_review import ReviewDialog
    from bodega.ui.dialogs.settings import PANES, SettingsDialog
    from tests.test_importer import ROWS
    from tests.test_update import GITHUB_ANSWER

    found: list[str] = []
    seen: list[str] = []
    opened: list[QDialog] = []

    def shown(d: QDialog) -> int:
        d.show()
        where = f"{type(d).__name__} ({d.windowTitle()})"
        seen.append(where)
        look(d, where, found)
        if isinstance(d, SettingsDialog):  # every section, at its size and its smallest
            for key, _label, _icon in PANES:
                d.show_pane(key)
                look(d, f"Settings › {key}", found)
            d.resize(*tokens.SETTINGS_MIN)
            for key, _label, _icon in PANES:
                d.show_pane(key)
                look(d, f"Settings › {key}, smallest", found)
        d.reject()
        opened.append(d)
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", shown)
    lib = sample.fill(Library(data_folder).load())
    w = window(lib, tokens.WINDOW_SIZE)
    rental = next(iter(lib.rentals.values()))
    piece = next(i for i in lib.ordered_items() if not i.parent)

    w.open_settings("general")
    w.open_settings("profiles", add_profile=True)
    w.edit_client(True)
    w.check_rental(rental.id, False)
    w.check_rental(rental.id, True)
    w.attach_to(piece.id)
    w.add_to_package(next(iter(lib.packages)))
    w.add_to_rental(rental.id)
    w.open_feedback()
    w._release = update.parse_release(GITHUB_ANSWER)
    w.show_update()
    for ctx in (("rental", rental.id), ("kit", next(iter(lib.packages))), ("gear", "")):
        w.show_pages(ctx)
    book = openpyxl.Workbook()
    for row in ROWS:
        book.active.append(row)
    book.save(tmp_path / "Gear List.xlsx")
    w.import_file(tmp_path / "Gear List.xlsx")
    review = Result(
        [
            Change(piece.id, "name", piece.name, f"{piece.name} (Body Only)", "bhphotovideo.com"),
            Change(piece.id, "value", piece.value, "6998", "bhphotovideo.com"),
        ],
        ["Tilta Camera Cage: no page found for it."],
    )
    ReviewDialog("Update from Links", review, {piece.id: piece.name}, w).exec()
    common.confirm(w, f"Delete {piece.name}?", "Rentals that had it keep its name and price.", "Delete")
    common.notice(w, "Couldn't Open the Sheet", "Share it as Anyone with the link first, then try again.")
    common.ask_name(w, "New Group", "Move", placeholder="Pelican Cases", known=lib.groups())
    common.tidy_preview(w, [(it, it.group, "Lights") for it in list(lib.items.values())[:4]])
    common.about(w, __version__, str(data_folder))
    SignInDialog(w).exec()
    for d in opened:  # gone in order (each takes its own type-ahead list with it), not swept up in any order
        d.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    w.close()
    assert len(seen) >= 18, seen  # (each command really opened its window)
    assert found == [], "\n" + "\n".join(found)
