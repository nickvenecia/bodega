"""Updates: Bodega checks GitHub for a newer release and installs it in place.

How it works
- check(): asks GitHub's API for the latest release of REPO (a published release, not a draft or
  pre-release). Its tag (v2.3.0) is compared with bodega.__version__.
- install_kind(): how this copy of Bodega was installed, which decides what to download:
    mac-app            Bodega.app (from the .dmg)                 -> the .dmg for this Mac's chip
    windows-installed  installed with Bodega-windows-setup.exe    -> the setup .exe, run silently
    windows-portable   the portable .zip                         -> the .zip, swapped in place
    appimage           Bodega-linux-x64.AppImage                  -> the AppImage, swapped in place
    linux-folder       the .tar.gz folder (install.sh)           -> the .tar.gz, swapped in place
    source             running from the code (python -m bodega)   -> nothing: pull the code instead
- download(): fetches the file into a temp folder, checks its size and its SHA-256 (GitHub
  publishes a digest for every release file).
- prepare(): unpacks what needs unpacking and writes a small helper script that waits for Bodega to
  quit, puts the new version where the old one was, and opens it again. MainWindow runs it and quits.

Nothing is sent except the request for the release list (no IDs, no usage data). The check runs at
most once a day, and can be turned off.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from bodega import __version__
from bodega.core.log import get_logger
from bodega.core.net import ssl_context
from bodega.core.paths import data_dir

log = get_logger(__name__)

REPO = "nickvenecia/bodega"  # github.com/<owner>/<repo> the releases come from
API = f"https://api.github.com/repos/{REPO}/releases/latest"
PAGE = f"https://github.com/{REPO}/releases/latest"
CHECK_EVERY_S = 20 * 3600  # the automatic check: at most about once a day


class Canceled(Exception):
    pass


@dataclass
class Asset:
    name: str
    url: str
    size: int = 0
    sha256: str = ""  # from GitHub's "digest" ("sha256:<hex>"), when it has one


@dataclass
class Release:
    version: str  # "2.3.0"
    notes: str = ""  # the release's text (Markdown)
    page: str = PAGE
    assets: dict[str, Asset] = field(default_factory=dict)

    @property
    def newer(self) -> bool:
        return is_newer(self.version, __version__)


def version_tuple(v: str) -> tuple[int, ...]:
    """'v2.10.1' -> (2, 10, 1); anything after a '-' or '+' (2.3.0-beta) is ignored."""
    v = v.strip().lstrip("vV").split("-")[0].split("+")[0]
    out = []
    for part in v.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        out.append(int(digits) if digits else 0)
    while len(out) < 3:
        out.append(0)
    return tuple(out)


def is_newer(latest: str, current: str) -> bool:
    return version_tuple(latest) > version_tuple(current)


def parse_release(data: dict) -> Release:
    assets = {}
    for a in data.get("assets") or []:
        digest = str(a.get("digest") or "")
        assets[a["name"]] = Asset(
            a["name"],
            a.get("browser_download_url", ""),
            int(a.get("size") or 0),
            digest.split(":", 1)[1].lower() if digest.startswith("sha256:") else "",
        )
    return Release(
        version=str(data.get("tag_name") or "0").lstrip("vV"),
        notes=str(data.get("body") or ""),
        page=str(data.get("html_url") or PAGE),
        assets=assets,
    )


def check(timeout: float = 15) -> Release:
    """The latest release on GitHub. Raises OSError (no internet, GitHub down) or ValueError."""
    req = urllib.request.Request(
        API,
        headers={
            "User-Agent": f"Bodega/{__version__}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as r:
        data = json.loads(r.read().decode("utf-8"))
    rel = parse_release(data)
    log.info("update check: latest %s, this is %s", rel.version, __version__)
    return rel


# ---------------------------------------------------------------------------- this copy of Bodega
def install_kind() -> str:
    if not getattr(sys, "frozen", False):
        return "source"
    exe = Path(sys.executable)
    if sys.platform == "darwin":
        return "mac-app" if app_bundle() else "source"
    if sys.platform == "win32":
        return "windows-installed" if any(exe.parent.glob("unins*.exe")) else "windows-portable"
    if os.environ.get("APPIMAGE") and _inside_appimage():
        return "appimage"
    return "linux-folder"


def _inside_appimage() -> bool:
    """APPIMAGE is passed down to programs an AppImage starts, so only trust it when Bodega itself runs
    from inside the AppImage (else another app's AppImage could be the one replaced)."""
    appdir = os.environ.get("APPDIR")
    return bool(appdir) and Path(sys.executable).resolve().is_relative_to(Path(appdir).resolve())


def app_bundle() -> Path | None:
    """Bodega.app around the running program (…/Bodega.app/Contents/MacOS/Bodega)."""
    for p in Path(sys.executable).resolve().parents:
        if p.suffix == ".app":
            return p
    return None


def asset_name(kind: str, machine: str | None = None) -> str | None:
    """Which release file updates this kind of install (the names CI gives them)."""
    machine = (machine or platform.machine()).lower()
    if kind == "mac-app":
        # A Bodega built for Intel runs on Apple Silicon under Rosetta: ask the Mac what it really is.
        arm = machine in ("arm64", "aarch64") or _mac_is_arm()
        return "Bodega-mac-apple-silicon.dmg" if arm else "Bodega-mac-intel.dmg"
    return {
        "windows-installed": "Bodega-windows-setup.exe",
        "windows-portable": "Bodega-windows-portable.zip",
        "appimage": "Bodega-linux-x64.AppImage",
        "linux-folder": "Bodega-linux-x64.tar.gz",
    }.get(kind)


def _mac_is_arm() -> bool:
    if sys.platform != "darwin":
        return False
    try:
        out = subprocess.run(
            ["/usr/sbin/sysctl", "-n", "hw.optional.arm64"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() == "1"
    except (OSError, subprocess.SubprocessError):
        return False


def target(kind: str) -> Path | None:
    """What gets replaced: the .app, the program folder, or the AppImage file."""
    if kind == "mac-app":
        return app_bundle()
    if kind in ("windows-installed", "windows-portable", "linux-folder"):
        return Path(sys.executable).resolve().parent
    if kind == "appimage":
        return Path(os.environ["APPIMAGE"])
    return None


def can_update_here(kind: str) -> str:
    """'' if Bodega can update itself; otherwise why not, in plain words."""
    if kind == "source":
        return "This copy of Bodega runs from its code. Get the new version with GitHub Desktop (Fetch, then Pull)."
    t = target(kind)
    if t is None:
        return "Couldn't find where Bodega is installed."
    if kind == "windows-installed":
        return ""  # the installer handles it
    if _overlaps(t, data_dir()):  # replacing the program would take your gear with it
        return "Bodega is installed inside its data folder, so it can't replace itself. Download the new version from GitHub."
    if not os.access(t.parent, os.W_OK):
        return f"Bodega can't write to {t.parent}. Download the new version from GitHub instead."
    return ""


def _overlaps(a: Path, b: Path) -> bool:
    a, b = a.resolve(), b.resolve()
    return a == b or a.is_relative_to(b) or b.is_relative_to(a)


# ---------------------------------------------------------------------------- download + install
DOWNLOAD_FROM = f"https://github.com/{REPO}/releases/download/"
DOWNLOAD_HOSTS = ("github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com")


def _trusted(url: str, hosts: tuple[str, ...] | None = None) -> bool:
    """A release file's link: Bodega's own releases page (or, after GitHub's redirect, its file hosts)."""
    if hosts is None:
        return url.startswith(DOWNLOAD_FROM)
    u = urllib.parse.urlparse(url)
    return u.scheme == "https" and u.hostname in hosts


def download(
    asset: Asset,
    folder: Path,
    on_progress: Callable[[float], None],
    cancel: threading.Event | None = None,
) -> Path:
    """Fetch one release file into `folder`, checking where it comes from, its size and its SHA-256.
    Nothing is installed that GitHub didn't publish a checksum for. Returns its path."""
    if not _trusted(asset.url):
        raise ValueError("That update isn't from Bodega's GitHub releases, so it wasn't used.")
    if not asset.sha256:
        raise ValueError(
            "GitHub didn't say what the update should look like, so it wasn't used. Try again later."
        )
    out = folder / asset.name
    req = urllib.request.Request(asset.url, headers={"User-Agent": f"Bodega/{__version__}"})
    h = hashlib.sha256()
    got = 0
    with (
        urllib.request.urlopen(req, timeout=60, context=ssl_context()) as r,
        out.open("wb") as f,
    ):
        if not _trusted(r.geturl(), DOWNLOAD_HOSTS):  # where GitHub's redirect ended up
            raise ValueError("The update came from somewhere unexpected, so it wasn't used.")
        total = int(r.headers.get("Content-Length") or asset.size or 0)
        while True:
            if cancel is not None and cancel.is_set():
                raise Canceled()
            chunk = r.read(512 * 1024)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            got += len(chunk)
            if total:
                on_progress(min(1.0, got / total))
    if asset.size and got != asset.size:
        raise ValueError(f"The download was cut short ({got} of {asset.size} bytes). Try again.")
    if h.hexdigest() != asset.sha256:
        raise ValueError("The download doesn't match what GitHub published, so it wasn't used. Try again.")
    log.info("update: downloaded %s (%d bytes, sha256 %s)", asset.name, got, h.hexdigest())
    return out


@dataclass
class Plan:
    """How to finish: run `command` (detached), then quit Bodega."""

    command: list[str]
    script: Path


def prepare(kind: str, file: Path, pid: int | None = None) -> Plan:
    """Unpack the download if needed and write the helper that swaps the new version in once Bodega
    has quit (pid), then opens it."""
    pid = pid or os.getpid()
    work = file.parent
    t = target(kind)
    if t is None:
        raise ValueError("Couldn't find where Bodega is installed.")
    if kind == "windows-installed":
        return _windows_script(
            work,
            pid,
            [f'"{file}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART'],
            t / "Bodega.exe",
        )
    if kind == "windows-portable":
        new = _unpack_zip(file, work)
        swap = [f'robocopy "{new}" "{t}" /MIR /R:3 /W:1 /NFL /NDL /NJH /NJS >NUL']
        return _windows_script(work, pid, swap, t / "Bodega.exe")
    if kind == "mac-app":
        return _posix_script(
            work,
            pid,
            [
                'MNT="$(mktemp -d)"',
                f'hdiutil attach -nobrowse -readonly -noautoopen -mountpoint "$MNT" {_q(file)} || exit 1',
                f'NEW={_q(t)}".new.$$"',
                'ditto "$MNT/Bodega.app" "$NEW"; OK=$?',
                'hdiutil detach "$MNT" -quiet',
                "[ $OK -eq 0 ] || exit 1",
                *_signature_lines(t, '"$NEW"'),
                'xattr -dr com.apple.quarantine "$NEW" 2>/dev/null',
                *_swap_lines(t, '"$NEW"'),
                f"open {_q(t)}",
            ],
        )
    if kind == "appimage":
        new = t.with_name(t.name + ".new")
        shutil.copy2(file, new)
        new.chmod(new.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return _posix_script(work, pid, [f"mv -f {_q(new)} {_q(t)}", f"({_q(t)} >/dev/null 2>&1 &)"])
    if kind == "linux-folder":
        new = _unpack_tar(file, work)
        return _posix_script(
            work,
            pid,
            [*_swap_lines(t, _q(new)), f"({_q(t / 'Bodega')} >/dev/null 2>&1 &)"],
        )
    raise ValueError("This copy of Bodega can't update itself.")


def run(plan: Plan) -> None:
    """Start the helper so it outlives Bodega."""
    log.info("update: starting %s", shlex.join(plan.command))
    if sys.platform == "win32":
        flags = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
        )
        subprocess.Popen(plan.command, creationflags=flags, close_fds=True)
    else:
        subprocess.Popen(plan.command, start_new_session=True, close_fds=True)


def _q(p) -> str:
    return shlex.quote(str(p))


def _signature_lines(old: Path, new: str) -> list[str]:
    """If this Bodega is signed by a developer (it has a Team ID), the new one must be signed by the same
    one, or it's thrown away. An unsigned build (no Team ID) relies on the download's checksum."""
    team = "codesign -dv {} 2>&1 | sed -n 's/^TeamIdentifier=//p'"
    requirement = 'anchor apple generic and certificate leaf[subject.OU] = \\"$OLD_TEAM\\"'
    return [
        f"OLD_TEAM=$({team.format(_q(old))})",
        'if [ -n "$OLD_TEAM" ] && [ "$OLD_TEAM" != "not set" ]; then',
        f'  if ! codesign --verify --deep --strict -R="={requirement}" {new}; then',
        f"    rm -rf {new}; exit 1",
        "  fi",
        "fi",
    ]


def _swap_lines(old: Path, new: str) -> list[str]:
    """Move the old version aside, the new one in, and only then delete the old one (if the move
    fails, put the old one back)."""
    return [
        f'OLD={_q(old)}".old.$$"',
        f'mv {_q(old)} "$OLD" || exit 1',
        f'if mv {new} {_q(old)}; then rm -rf "$OLD"; else mv "$OLD" {_q(old)}; exit 1; fi',
    ]


def _posix_script(
    work: Path,
    pid: int,
    lines: list[str],
) -> Plan:
    script = work / "finish-update.sh"
    body = [
        "#!/bin/bash",
        "# Written by Bodega: waits for Bodega to quit, swaps in the new version, opens it.",
        f"exec >>{_q(work / 'finish-update.log')} 2>&1",
        f"while kill -0 {pid} 2>/dev/null; do sleep 0.3; done",
        *lines,
        f"rm -rf {_q(work)}",
    ]
    script.write_text("\n".join(body) + "\n", encoding="utf-8")
    script.chmod(0o755)
    return Plan(["/bin/bash", str(script)], script)


def _windows_script(work: Path, pid: int, lines: list[str], exe: Path) -> Plan:
    script = work / "finish-update.cmd"
    body = [
        "@echo off",
        "rem Written by Bodega: waits for Bodega to quit, installs the new version, opens it.",
        ":wait",
        f'tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL && (timeout /t 1 /nobreak >NUL & goto wait)',
        *lines,
        f'start "" "{exe}"',
        f'rmdir /s /q "{work}"',
    ]
    script.write_text("\r\n".join(body) + "\r\n", encoding="utf-8")
    return Plan(["cmd.exe", "/c", str(script)], script)


def _unpack_zip(file: Path, work: Path) -> Path:
    dest = work / "unpacked"
    with zipfile.ZipFile(file) as z:
        for m in z.namelist():
            p = (dest / m).resolve()
            if not p.is_relative_to(dest.resolve()):
                raise ValueError("The update file looks wrong, so it wasn't used.")
        z.extractall(dest)  # noqa: S202 — every path checked above
    inner = dest / "Bodega"
    return inner if inner.is_dir() else dest


def _unpack_tar(file: Path, work: Path) -> Path:
    dest = work / "unpacked"
    dest.mkdir(exist_ok=True)
    with tarfile.open(file) as t:
        t.extractall(dest, filter="data")
    inner = dest / "Bodega"
    return inner if inner.is_dir() else dest


def new_work_folder() -> Path:
    return Path(tempfile.mkdtemp(prefix="bodega-update-"))
