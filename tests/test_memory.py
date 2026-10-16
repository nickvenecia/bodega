"""Opening and closing screens leaves nothing behind (the standard's T-06): after a warm-up, a few more rounds of
every screen (places, pieces, kits, rentals, Settings, the palette, the page window, the assistant) leave the same
widgets alive and use next to no more memory. A window that stayed in memory after it closed (Settings: about 700
widgets and 1 MB each time) once grew Bodega all day."""

from __future__ import annotations

import gc
import tracemalloc

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QDialog

from bodega.core import sample
from bodega.core.store import Library

ROUNDS = 3
MEMORY_LIMIT_KB = 600  # what the rounds may add (caches filling up), all told; a leak adds about 1 MB a round


def test_opening_and_closing_screens_leaves_nothing_behind(qapp, data_folder, monkeypatch):
    from bodega.ui.window.main_window import MainWindow

    def opened_and_closed(d):  # every window on top opens, draws, and closes again
        d.show()
        QApplication.processEvents()
        QDialog.done(d, 0)
        return 0

    monkeypatch.setattr(QDialog, "exec", opened_and_closed)
    lib = sample.fill(Library(data_folder).load())
    w = MainWindow(lib)
    w.show()
    QApplication.processEvents()

    def settle():
        for _ in range(3):
            QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            QApplication.processEvents()
        gc.collect()

    def one_round():
        for item_id in list(lib.items)[:6]:
            w.open("gear", item_id)
        for kind, records in (("rentals", lib.rentals), ("packages", lib.packages)):
            for obj_id in records:
                w.open(kind, obj_id)
        for place in ("calendar", "kits", "rentals", "out", "gear"):
            w.go(place)
        w.open_settings("profiles")
        w.open_settings("general")
        w.search_everything()
        w.show_pages(("rental", next(iter(lib.rentals))))
        w.show_pages(("gear", ""), "labels")
        w.toggle_assistant()
        w.toggle_assistant()
        settle()

    one_round()
    one_round()  # warmed up: every cache that fills once has
    widgets = len(QApplication.allWidgets())
    tracemalloc.start()
    try:
        start = tracemalloc.get_traced_memory()[0]
        for _ in range(ROUNDS):
            one_round()
        grew_kb = (tracemalloc.get_traced_memory()[0] - start) // 1024
    finally:
        tracemalloc.stop()
    assert len(QApplication.allWidgets()) == widgets, "a screen left widgets behind"
    assert grew_kb < MEMORY_LIMIT_KB, f"{ROUNDS} rounds of screens kept {grew_kb} KB"
    w.close()


def test_cycles_are_collected_only_on_the_windows_thread(qapp):
    """Python's own collector is off (it would run on any thread, mid-Qt); Bodega's runs between events, on the
    window's thread, and frees what's left in cycles."""
    import gc
    import weakref

    assert not gc.isenabled() and qapp._gc.timer.isActive()

    class Loop:
        pass

    gc.collect()  # (a clean start: nothing older is due)
    a, b = Loop(), Loop()
    a.other, b.other = b, a
    gone = weakref.ref(a)
    del a, b
    assert gone() is not None  # a cycle: counting references alone never frees it
    made = [[] for _ in range(gc.get_threshold()[0] + 1)]  # enough made that a collection is due
    qapp._gc.collect()
    assert gone() is None and made
