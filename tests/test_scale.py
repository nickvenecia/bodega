"""A rental house's worth: 3,000 pieces (a third attached to another) and 2,000 rentals. Bodega stays quick at
that size (the standard's P-13): the limits are several times what a laptop takes, so a slow CI machine passes and
a pass that looks through every piece for every piece again (as it once did, seconds each) fails."""

from __future__ import annotations

import random
import time

import pytest

from bodega.core import earnings, pricing, sample
from bodega.core.model import Item, Rental, RentalLine
from bodega.core.store import Library

LIMITS_S = {
    "earnings": 2.0,
    "shortages": 0.5,
    "open": 8.0,
    "refresh": 4.0,
    "open a piece": 1.5,
    "undo mark": 1.0,
    "open a rental": 1.5,
    "change a rental": 2.0,
    "undo": 4.0,
    "tidy": 1.0,
    "import": 6.0,
    "delete 300": 6.0,
    "apply 300 changes": 1.5,
}


@pytest.fixture(scope="module")
def big(tmp_path_factory):
    lib = sample.fill(Library(tmp_path_factory.mktemp("big")).load())
    rnd = random.Random(1)  # noqa: S311 (made-up gear, the same every run)
    groups = ["Body", "Lenses", "Lights", "Grip", "Audio", "Media", "Batteries", "Monitoring"]
    ids: list[str] = []
    for n in range(3000):
        it = Item(
            name=f"Piece {n}",
            group=rnd.choice(groups),
            qty=rnd.randint(1, 4),
            value=str(rnd.randint(50, 9000)),
        )
        if ids and rnd.random() < 0.3:
            it.parent = rnd.choice(ids)
        lib.items[it.id] = it
        ids.append(it.id)
    for _n in range(2000):
        day = f"2026-{rnd.randint(1, 12):02d}-{rnd.randint(1, 27):02d}"
        r = Rental(status=rnd.choice(["quote", "booked", "out", "returned"]), pickup=day, return_date=day)
        r.lines = [RentalLine("item", rnd.choice(ids), 1) for _ in range(5)]
        lib.rentals[r.id] = r
    return lib


def timed(f) -> float:
    start = time.perf_counter()
    f()
    return time.perf_counter() - start


def test_the_rules_stay_quick_at_a_rental_houses_size(big):
    assert timed(lambda: earnings.earnings(big)) < LIMITS_S["earnings"]
    r = next(iter(big.rentals.values()))
    assert timed(lambda: pricing.shortages(big, r)) < LIMITS_S["shortages"]


def test_the_window_stays_quick_at_a_rental_houses_size(qapp, big):
    from PySide6.QtWidgets import QApplication

    from bodega.ui.window.main_window import MainWindow

    holder = {}

    def opened():
        holder["w"] = MainWindow(big)
        holder["w"].show()
        QApplication.processEvents()

    assert timed(opened) < LIMITS_S["open"]
    w = holder["w"]
    assert timed(lambda: (w.refresh(), QApplication.processEvents())) < LIMITS_S["refresh"]
    piece = next(i for i in big.items.values() if i.name.startswith("Piece"))
    assert timed(lambda: (w.open("gear", piece.id), QApplication.processEvents())) < LIMITS_S["open a piece"]
    assert timed(w.history.mark) < LIMITS_S["undo mark"]
    r = next(r for r in big.rentals.values() if r.lines and r.is_quote())
    assert timed(lambda: (w.open("rentals", r.id), QApplication.processEvents())) < LIMITS_S["open a rental"]

    def changed():
        r.lines[0].qty += 1
        w.rentals.changed.emit(r)
        w.flush()
        QApplication.processEvents()

    assert timed(changed) < LIMITS_S["change a rental"]
    assert timed(lambda: (w.undo(), QApplication.processEvents())) < LIMITS_S["undo"]
    w.close()


def test_the_big_jobs_stay_quick_at_a_rental_houses_size(big, tmp_path):
    """Tidy Up Groups, an import of every piece, approving many changes and deleting many at once (last: they
    change the library)."""
    from bodega.core import importer, tidy

    assert timed(lambda: tidy.changes(big.items)) < LIMITS_S["tidy"]
    sheet = importer.write_csv(list(big.items.values()), big.items, tmp_path / "all.csv")
    assert timed(lambda: importer.read(sheet)) < LIMITS_S["import"]
    from bodega.services.ai import tasks

    pieces = [i for i in big.items.values() if i.name.startswith("Piece")]
    changes = [tasks.Change(i.id, "name", i.name, f"{i.name} Mk II") for i in pieces[:200]]
    changes += [tasks.Change(i.id, "group", i.group, "Grip") for i in pieces[200:300]]
    assert timed(lambda: tasks.apply(big, changes)) < LIMITS_S["apply 300 changes"]  # (Review's Change 300 Pieces)
    ids = [i.id for i in pieces[300:600]]
    assert timed(lambda: big.delete_items(ids)) < LIMITS_S["delete 300"]
    assert not any(i in big.items for i in ids)
