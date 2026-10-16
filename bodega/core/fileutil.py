"""Showing a file in Finder / Explorer / the Linux file manager."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from bodega.core.log import get_logger

log = get_logger(__name__)


def popen_kwargs() -> dict:
    """Keeps Windows from flashing a console window."""
    if sys.platform == "win32":
        return {"creationflags": 0x08000000}  # CREATE_NO_WINDOW
    return {}


def reveal(path: str | Path) -> None:
    """Open the folder with this file selected (Linux: just the folder)."""
    path = str(path)
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)], **popen_kwargs())
        else:
            target = path if os.path.isdir(path) else os.path.dirname(path)
            subprocess.Popen(["xdg-open", target])
    except OSError:
        log.warning("couldn't show %s", os.path.basename(path), exc_info=True)


def zip_folder(folder: Path, dest: Path, skip: tuple[str, ...] = (), progress=None, cancel=None) -> int | None:
    """Copy everything in `folder` into the zip file `dest` (written beside it first, then swapped in).
    Top-level names in `skip` are left out. Returns how many files went in, or None if `cancel` was set first
    (then nothing is left behind). `progress(done, total)` hears each file."""
    import zipfile

    folder, dest = Path(folder), Path(dest)
    tmp = dest.with_name(dest.name + ".part")
    chosen = [
        path
        for path in sorted(folder.rglob("*"))
        if path.is_file() and path.relative_to(folder).parts[0] not in skip and path not in (tmp, dest)
    ]
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for n, path in enumerate(chosen):
                if cancel is not None and cancel.is_set():
                    break
                if progress is not None:
                    progress(n, len(chosen))
                z.write(path, Path(folder.name) / path.relative_to(folder))
            else:
                n = len(chosen)
        if cancel is not None and cancel.is_set():
            tmp.unlink(missing_ok=True)
            return None
        os.replace(tmp, dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return len(chosen)
