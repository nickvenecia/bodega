"""Safety copies and Restore (core/backups.py, Library.restore, File › Restore from Backup…)."""

from __future__ import annotations

import zipfile

import pytest

from bodega.core import backups, sample
from bodega.core.fileutil import zip_folder
from bodega.core.store import Library
from tests.ui import type_into


def _lib(folder) -> Library:
    return sample.fill(Library(folder).load())


def test_a_safety_copy_each_day_and_the_newest_kept(data_folder, monkeypatch):
    lib = _lib(data_folder)
    first = backups.daily_copy(lib.root)
    assert first is not None and backups.daily_copy(lib.root) is None  # once a day
    with zipfile.ZipFile(first) as z:
        assert {"gear.json", "businesses.json"} <= set(z.namelist())
        assert any(n.startswith("rentals/") for n in z.namelist())
    monkeypatch.setattr(backups, "CHANGES_KEPT", 3)
    for i in range(5):
        (backups.folder(lib.root) / f"Bodega 2026-01-0{i + 1} 090000 before-import.zip").write_bytes(b"")
    backups.prune(lib.root)
    others = [p for p in backups.copies(lib.root) if not p.stem.endswith("daily")]
    assert len(others) == 3 and first.exists()


def test_a_back_up_zip_puts_everything_back(data_folder, tmp_path):
    lib = _lib(data_folder)
    zip_folder(lib.root, tmp_path / "Bodega Backup.zip", skip=("ui",))
    it = next(iter(lib.items.values()))
    was = it.name
    it.name = "Changed After the Backup"
    lib.save_items()
    r = next(iter(lib.rentals.values()))
    lib.delete_rental(r.id)
    backup = backups.read_backup(tmp_path / "Bodega Backup.zip")
    assert "pieces of gear" in backup.summary() and "1 rental" in backup.summary()
    kept = lib.restore(backup)
    assert lib.items[it.id].name == was and r.id in lib.rentals
    assert kept is not None and kept.exists()  # how things were, kept in turn…
    lib.restore(backups.read_backup(kept))  # …so the restore can be undone
    assert lib.items[it.id].name == "Changed After the Backup" and r.id not in lib.rentals


def test_a_restore_never_gives_a_number_again(data_folder):
    lib = _lib(data_folder)
    b = next(iter(lib.businesses.values()))
    copy = backups.safety_copy(lib.root, "test")
    newer = lib.new_rental(b)  # made after the copy: the restore takes it away…
    lib.restore(backups.read_backup(copy))
    assert newer.id not in lib.rentals
    assert lib.new_rental(b).number != newer.number  # …but its number stays spent


def test_a_restore_adds_missing_photos_and_deletes_none(data_folder, tmp_path):
    lib = _lib(data_folder)
    photos = lib.root / "photos"
    photos.mkdir(parents=True, exist_ok=True)
    (photos / "old.jpg").write_bytes(b"old")
    zip_folder(lib.root, tmp_path / "b.zip")
    (photos / "old.jpg").unlink()
    (photos / "new.jpg").write_bytes(b"new")
    lib.restore(backups.read_backup(tmp_path / "b.zip"))
    assert (photos / "old.jpg").read_bytes() == b"old" and (photos / "new.jpg").exists()


def _zip(path, files: dict[str, bytes]):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return path


@pytest.mark.parametrize(
    ("files", "says"),
    [
        ({"../gear.json": b"[]"}, "outside"),
        ({"/etc/gear.json": b"[]"}, "outside"),
        ({"gear.json": b"{not json"}, "can't be read"),
        ({"gear.json": b'{"a": 1}'}, "can't be read"),  # the wrong shape
        ({"rentals/a.json": b"[]"}, "can't be read"),
        ({"notes.txt": b"hello"}, "isn't a Bodega backup"),
    ],
)
def test_a_backup_is_read_as_untrusted(tmp_path, files, says):
    with pytest.raises(ValueError, match=says):
        backups.read_backup(_zip(tmp_path / "x.zip", files))


def test_something_that_isnt_a_zip_is_said_plainly(tmp_path):
    (tmp_path / "x.zip").write_text("not a zip", encoding="utf-8")
    with pytest.raises(ValueError, match="isn't a Bodega backup"):
        backups.read_backup(tmp_path / "x.zip")


def test_a_file_too_big_to_be_bodegas_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(backups, "MAX_FILE", 10)
    with pytest.raises(ValueError, match="too big"):
        backups.read_backup(_zip(tmp_path / "x.zip", {"gear.json": b"[" + b" " * 20 + b"]"}))


def test_only_bodegas_own_places_come_back(tmp_path):
    b = backups.read_backup(
        _zip(
            tmp_path / "x.zip",
            {
                "Bodega/gear.json": b"[]",
                "Bodega/logs/bodega.log": b"log",
                "Bodega/backups/Bodega old.zip": b"zip",
                "Bodega/rentals/bad name.json": b"{}",
                "Bodega/photos/.hidden": b"x",
                "Bodega/photos/a.jpg": b"jpg",
            },
        )
    )
    assert set(b.files) == {"gear.json", "photos/a.jpg"}


def test_restore_from_the_window(qapp, data_folder, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    from bodega.ui.dialogs import common
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(_lib(data_folder))
    assert "Restore from Backup…" in [a.text() for m in w.menuBar().actions() for a in m.menu().actions()]
    zip_folder(w.lib.root, tmp_path / "b.zip")
    it = next(iter(w.lib.items.values()))
    was = it.name
    w.open("gear", it.id)
    type_into(w.items.name, "Changed")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(tmp_path / "b.zip"), ""))
    monkeypatch.setattr(common, "confirm", lambda *a, **k: True)
    w.restore()
    assert w.lib.items[it.id].name == was
    assert Library(data_folder).load().items[it.id].name == was
    assert not w.history.undos  # undo starts again from what came back
    w.close()


def test_a_back_up_stopped_part_way_leaves_nothing_behind(data_folder, tmp_path):
    import threading

    lib = sample.fill(Library(data_folder).load())
    dest = tmp_path / "Bodega Backup.zip"
    cancel = threading.Event()
    heard = []

    def progress(n, total):
        heard.append((n, total))
        if n == 1:
            cancel.set()  # Stop, while the second file goes in

    assert zip_folder(lib.root, dest, progress=progress, cancel=cancel) is None
    assert heard[0][0] == 0 and heard[0][1] > 2
    assert not dest.exists() and not list(tmp_path.glob("*.part"))
    assert zip_folder(lib.root, dest, progress=lambda *_a: None) == heard[0][1]  # and done again, all of it
