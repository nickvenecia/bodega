"""Safety copies and Restore.

Bodega keeps a copy of your records (gear, kits, rentals, renters, profiles, settings) each day it opens and before
a big change (an import, Tidy Up Groups, an AI's changes), in the data folder's backups/: the newest DAILY_KEPT
daily copies and CHANGES_KEPT of the others. A safety copy or a Back Up zip can be put back with Restore. Photos and
logos are never deleted, so copies leave them out and a restore only adds the ones that are missing.

A backup is read as untrusted: only Bodega's own files, in their own places, of sane sizes, and every record must
read before anything is replaced. No Qt here.
"""

from __future__ import annotations

import json
import os
import re
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from bodega.core.log import get_logger

log = get_logger(__name__)

RECORDS = {  # file -> what it holds (a list of records, or the settings)
    "gear.json": list,
    "packages.json": list,
    "clients.json": list,
    "businesses.json": list,
    "settings.json": dict,
}
DAILY_KEPT = 14
CHANGES_KEPT = 20
MAX_FILE = 64 * 1024 * 1024  # one file in a backup (a photo is scaled well under this)
MAX_TOTAL = 4 * 1024 * 1024 * 1024
MAX_FILES = 100_000
_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}\.json$")
_NAME = re.compile(r"^[^/\\:*?\"<>|\x00-\x1f]{1,200}$")  # a photo's or a logo's file name


def folder(root: Path) -> Path:
    return Path(root) / "backups"


def record_files(root: Path) -> list[Path]:
    root = Path(root)
    files = [root / name for name in RECORDS if (root / name).is_file()]
    rentals = root / "rentals"
    if rentals.is_dir():
        files += sorted(p for p in rentals.glob("*.json") if p.is_file())
    return files


def safety_copy(root: Path, why: str) -> Path | None:
    """A zip of every record, in backups/ ("Bodega 2026-10-16 093012 before-import.zip"). None if there's
    nothing to copy yet or it couldn't be written (that's logged; the change goes ahead)."""
    root = Path(root)
    files = record_files(root)
    if not files:
        return None
    why = re.sub(r"[^a-z0-9-]", "", why.lower()) or "copy"
    dest = folder(root) / f"Bodega {time.strftime('%Y-%m-%d %H%M%S')} {why}.zip"
    tmp = dest.with_name(dest.name + ".part")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for path in files:
                z.write(path, path.relative_to(root).as_posix())
        os.replace(tmp, dest)
    except OSError:
        log.warning("couldn't keep a safety copy (%s)", why, exc_info=True)
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    prune(root)
    return dest


def daily_copy(root: Path) -> Path | None:
    """Today's safety copy, the first time Bodega opens today (None if there is one already)."""
    if list(folder(root).glob(f"Bodega {time.strftime('%Y-%m-%d')} * daily.zip")):
        return None
    return safety_copy(root, "daily")


def copies(root: Path) -> list[Path]:
    """Every safety copy, newest first."""
    return sorted(folder(root).glob("Bodega *.zip"), reverse=True)


def prune(root: Path) -> None:
    daily = [p for p in copies(root) if p.stem.endswith(" daily")]
    others = [p for p in copies(root) if not p.stem.endswith(" daily")]
    for old in daily[DAILY_KEPT:] + others[CHANGES_KEPT:]:
        try:
            old.unlink()
        except OSError:
            log.warning("couldn't remove the old safety copy %s", old.name, exc_info=True)


@dataclass
class Backup:
    """A backup, read and checked: its files by their place in the data folder."""

    path: Path
    files: dict[str, bytes] = field(default_factory=dict)

    def records(self, name: str) -> list:
        data = self.files.get(name)
        return json.loads(data) if data is not None else []

    def rentals(self) -> dict[str, bytes]:
        return {k: v for k, v in self.files.items() if k.startswith("rentals/")}

    def summary(self) -> str:
        """ "38 pieces of gear, 1 kit and 2 rentals"."""

        def n(count: int, one: str, many: str) -> str:
            return f"{count:,} {one if count == 1 else many}"

        parts = [
            n(len(self.records("gear.json")), "piece of gear", "pieces of gear"),
            n(len(self.records("packages.json")), "kit", "kits"),
            n(len(self.rentals()), "rental", "rentals"),
        ]
        return ", ".join(parts[:-1]) + " and " + parts[-1]


def _place(rel: PurePosixPath) -> str | None:
    """Where a file in a backup goes in the data folder, or None to leave it out (logs, older copies…)."""
    parts = rel.parts
    if len(parts) == 1 and parts[0] in RECORDS:
        return parts[0]
    if len(parts) == 2 and parts[0] == "rentals" and _ID.match(parts[1]):
        return rel.as_posix()
    if len(parts) == 2 and parts[0] in ("photos", "logos") and _NAME.match(parts[1]) and parts[1][0] != ".":
        return rel.as_posix()
    return None


def read_backup(path: Path) -> Backup:
    """Read a Back Up zip or a safety copy. Raises ValueError, in plain words, for anything that isn't one."""
    path = Path(path)
    try:
        z = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as e:
        raise ValueError("That file isn't a Bodega backup (it isn't a zip file Bodega can open).") from e
    with z:
        infos = [i for i in z.infolist() if not i.is_dir()]
        if len(infos) > MAX_FILES:
            raise ValueError("That backup has far more files in it than Bodega ever makes.")
        names = [PurePosixPath(i.filename.replace("\\", "/")) for i in infos]
        if any(p.is_absolute() or ".." in p.parts for p in names):
            raise ValueError("That backup has files that point outside its folder, so Bodega won't open it.")
        # Back Up puts everything in a folder named like the data folder: look inside it
        tops = {p.parts[0] for p in names if len(p.parts) > 1}
        inside = len(tops) == 1 and all(len(p.parts) > 1 for p in names) and _place(names[0]) is None
        backup = Backup(path)
        total = 0
        for info, name in zip(infos, names, strict=True):
            rel = PurePosixPath(*name.parts[1:]) if inside else name
            place = _place(rel)
            if place is None:
                continue
            if info.file_size > MAX_FILE:
                raise ValueError(f"{rel.name} in that backup is too big to be one of Bodega's files.")
            total += info.file_size
            if total > MAX_TOTAL:
                raise ValueError("That backup is too big to be one of Bodega's.")
            try:
                with z.open(info) as f:
                    data = f.read(MAX_FILE + 1)
            except (OSError, zipfile.BadZipFile, RuntimeError) as e:  # damaged, or locked with a password
                raise ValueError(f"{rel.name} in that backup can't be read.") from e
            if len(data) > MAX_FILE:
                raise ValueError(f"{rel.name} in that backup is too big to be one of Bodega's files.")
            if place.endswith(".json"):
                want = RECORDS.get(place, dict)
                try:
                    ok = isinstance(json.loads(data.decode("utf-8")), want)
                except (UnicodeDecodeError, ValueError):
                    ok = False
                if not ok:
                    raise ValueError(
                        f"{rel.as_posix()} in that backup can't be read, so nothing was restored."
                    )
            backup.files[place] = data
    if not any(k in RECORDS or k.startswith("rentals/") for k in backup.files):
        raise ValueError("That isn't a Bodega backup: there's no gear, kits, rentals or profiles in it.")
    return backup


def write_bytes(path: Path, data: bytes) -> None:
    """Write a file atomically: a temp file in the same folder, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.restoring")
    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            log.warning("couldn't remove %s", tmp.name, exc_info=True)
        raise


def put_back(root: Path, backup: Backup) -> None:
    """Make the data folder's records the backup's (the window keeps a safety copy first). A record file the
    backup doesn't have becomes empty, rentals it doesn't have go, and its photos and logos that are missing
    are added. Settings stay as they are unless the backup has its own."""
    root = Path(root)
    for name, kind in RECORDS.items():
        if name in backup.files:
            write_bytes(root / name, backup.files[name])
        elif kind is list and (root / name).exists():
            write_bytes(root / name, b"[]")
    keep = set(backup.rentals())
    rentals = root / "rentals"
    if rentals.is_dir():
        for f in rentals.glob("*.json"):
            if f"rentals/{f.name}" not in keep:
                f.unlink()
    for place, data in backup.files.items():
        missing = not (root / place).exists()  # a photo or a logo already here stays as it is
        if place.startswith("rentals/") or (place.startswith(("photos/", "logos/")) and missing):
            write_bytes(root / place, data)
