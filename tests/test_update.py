"""Updates (core/update.py, ui/update_dialog.py): finding a newer release, downloading it safely and
swapping it in once Bodega has quit."""

from __future__ import annotations

import hashlib
import http.server
import io
import os
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import zipfile
from pathlib import Path

import pytest

from bodega.core import update

GITHUB_ANSWER = {
    "tag_name": "v9.1.0",
    "html_url": "https://github.com/nickvenecia/bodega/releases/tag/v9.1.0",
    "body": "## Download\n| a | b |\n\n## What's new\n- Faster glitches",
    "assets": [
        {
            "name": "Bodega-mac-apple-silicon.dmg",
            "browser_download_url": "https://example.invalid/a.dmg",
            "size": 10,
            "digest": "sha256:ABCDEF",
        },
        {
            "name": "Bodega-linux-x64.AppImage",
            "browser_download_url": "https://example.invalid/b",
            "size": 5,
        },
    ],
}


def test_versions_compare_like_numbers():
    assert update.version_tuple("v2.10.1") == (2, 10, 1)
    assert update.version_tuple("3") == (3, 0, 0)
    assert update.is_newer("v2.10.0", "2.9.9")  # 10 > 9, not "1" < "9"
    assert not update.is_newer("2.3.0", "2.3.0")
    assert not update.is_newer("2.3.0-beta", "2.3.0")


def test_a_github_release_is_read_with_each_downloads_size_and_check():
    rel = update.parse_release(GITHUB_ANSWER)
    assert rel.version == "9.1.0" and rel.newer
    a = rel.assets["Bodega-mac-apple-silicon.dmg"]
    assert a.size == 10 and a.sha256 == "abcdef"
    assert rel.assets["Bodega-linux-x64.AppImage"].sha256 == ""


def test_the_right_file_for_each_kind_of_install():
    assert update.asset_name("mac-app", "arm64") == "Bodega-mac-apple-silicon.dmg"
    assert update.asset_name("windows-installed") == "Bodega-windows-setup.exe"
    assert update.asset_name("windows-portable") == "Bodega-windows-portable.zip"
    assert update.asset_name("appimage") == "Bodega-linux-x64.AppImage"
    assert update.asset_name("linux-folder") == "Bodega-linux-x64.tar.gz"
    assert update.asset_name("source") is None


def test_running_from_the_code_is_updated_with_git():
    assert update.install_kind() == "source"  # the tests run from the code
    assert "GitHub Desktop" in update.can_update_here("source")


class _Files(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture
def server(tmp_path: Path):
    root = tmp_path / "web"
    root.mkdir()
    handler = lambda *a, **k: _Files(*a, directory=str(root), **k)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield root, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_download_only_from_our_releases_with_a_checksum(tmp_path: Path):
    other = update.Asset("Bodega-linux-x64.AppImage", "https://example.com/Bodega.AppImage", 10, "0" * 64)
    with pytest.raises(ValueError, match="isn't from"):
        update.download(other, tmp_path, lambda _v: None)
    ours = f"https://github.com/{update.REPO}/releases/download/v9.9.9/Bodega-linux-x64.AppImage"
    unchecked = update.Asset("Bodega-linux-x64.AppImage", ours, 10, "")
    with pytest.raises(ValueError, match="didn't say"):
        update.download(unchecked, tmp_path, lambda _v: None)
    assert update._trusted(ours)
    assert not update._trusted("http://objects.githubusercontent.com/x", update.DOWNLOAD_HOSTS)


def test_download_checks_size_and_fingerprint(tmp_path: Path, server, monkeypatch):
    monkeypatch.setattr(update, "_trusted", lambda *_a: True)  # the test server stands in for GitHub
    root, base = server
    data = b"new bodega" * 1000
    (root / "f.AppImage").write_bytes(data)
    good = update.Asset(
        "Bodega-linux-x64.AppImage",
        f"{base}/f.AppImage",
        len(data),
        hashlib.sha256(data).hexdigest(),
    )
    seen = []
    out = update.download(good, tmp_path, seen.append)
    assert out.read_bytes() == data and seen and seen[-1] == 1.0
    bad = update.Asset("x", f"{base}/f.AppImage", len(data), "0" * 64)
    with pytest.raises(ValueError, match="doesn't match"):
        update.download(bad, tmp_path, lambda _v: None)
    short = update.Asset("y", f"{base}/f.AppImage", len(data) + 5, hashlib.sha256(data).hexdigest())
    with pytest.raises(ValueError, match="cut short"):
        update.download(short, tmp_path, lambda _v: None)


def _gone_pid() -> int:
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


def _wait_for(path: Path, timeout: float = 15) -> bool:
    end = time.monotonic() + timeout
    while not path.exists() and time.monotonic() < end:
        time.sleep(0.1)
    return path.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="Linux / Mac helper")
def test_appimage_is_swapped_and_reopened(tmp_path: Path, monkeypatch):
    app = tmp_path / "apps" / "Bodega-linux-x64.AppImage"
    app.parent.mkdir()
    app.write_text("old", encoding="utf-8")
    monkeypatch.setenv("APPIMAGE", str(app))
    opened = tmp_path / "opened"
    work = update.new_work_folder()
    new = work / "Bodega-linux-x64.AppImage"
    new.write_text(f"#!/bin/sh\ntouch {opened}\n", encoding="utf-8")
    plan = update.prepare("appimage", new, pid=_gone_pid())
    subprocess.run(plan.command, check=True, timeout=30)
    assert "touch" in app.read_text(encoding="utf-8") and os.access(app, os.X_OK)  # the new one, runnable
    assert _wait_for(opened)  # and it was opened
    assert not work.exists()  # the download is cleaned up


@pytest.mark.skipif(sys.platform == "win32", reason="Linux / Mac helper")
def test_linux_folder_is_swapped_and_reopened(tmp_path: Path, monkeypatch):
    folder = tmp_path / "bodega"
    folder.mkdir()
    (folder / "Bodega").write_text("old", encoding="utf-8")
    (folder / "leftover.txt").write_text("old file", encoding="utf-8")
    monkeypatch.setattr(update, "target", lambda _kind: folder)
    opened = tmp_path / "opened"
    work = update.new_work_folder()
    tar = work / "Bodega-linux-x64.tar.gz"
    with tarfile.open(tar, "w:gz") as t:
        script = f"#!/bin/sh\ntouch {opened}\n".encode()
        info = tarfile.TarInfo("Bodega/Bodega")
        info.size, info.mode = len(script), 0o755
        t.addfile(info, io.BytesIO(script))
    plan = update.prepare("linux-folder", tar, pid=_gone_pid())
    subprocess.run(plan.command, check=True, timeout=30)
    assert "touch" in (folder / "Bodega").read_text(encoding="utf-8")
    assert not (folder / "leftover.txt").exists()  # the whole folder is the new version
    assert _wait_for(opened)
    assert not list(tmp_path.glob("bodega.old.*"))


def test_mac_and_windows_helpers(tmp_path: Path, monkeypatch):
    app = tmp_path / "Applications" / "Bodega.app"
    monkeypatch.setattr(update, "target", lambda _kind: app)
    dmg = tmp_path / "Bodega-mac-apple-silicon.dmg"
    dmg.write_bytes(b"dmg")
    mac = update.prepare("mac-app", dmg, pid=4242).script.read_text(encoding="utf-8")
    for step in (
        "kill -0 4242",
        "hdiutil attach",
        "ditto",
        "com.apple.quarantine",
        "open ",
    ):
        assert step in mac, step

    folder = tmp_path / "Programs" / "Bodega"
    monkeypatch.setattr(update, "target", lambda _kind: folder)
    setup = tmp_path / "Bodega-windows-setup.exe"
    setup.write_bytes(b"exe")
    plan = update.prepare("windows-installed", setup, pid=4242)
    win = plan.script.read_text(encoding="utf-8-sig")
    assert plan.command[0] == "powershell.exe" and plan.script.suffix == ".ps1"
    assert "/VERYSILENT" in win and "Wait-Process -Id 4242" in win and "Bodega.exe" in win
    # (no pipes into console tools: a batch file's `tasklist | find` waited for ever when started on its own)
    assert "tasklist" not in win and "find.exe" not in win
    assert win.index("$p.ExitCode -ne 0") < win.rindex("Start-Process -FilePath '")  # a failed install opens nothing
    zipped = tmp_path / "Bodega-windows-portable.zip"
    with zipfile.ZipFile(zipped, "w") as z:
        z.writestr("Bodega/Bodega.exe", b"exe")
    portable = update.prepare("windows-portable", zipped, pid=4242).script.read_text(encoding="utf-8-sig")
    assert "robocopy" in portable and "$LASTEXITCODE -ge 8" in portable and "finish-update.log" in portable
    written = zipped.parent.joinpath("finish-update.ps1").read_bytes()  # (the script sits beside the download)
    assert written.startswith(b"\xef\xbb\xbf")  # UTF-8 with its mark: Windows' PowerShell reads é as written
    assert b"\r\r\n" not in written and written.count(b"\r\n") == written.count(b"\n")  # each line ends once
    odd = tmp_path / "it's here"
    monkeypatch.setattr(update, "target", lambda _kind: odd)
    quoted = "'" + str(odd / "Bodega.exe").replace("'", "''") + "'"
    assert quoted in update.prepare("windows-installed", setup, 1).script.read_text(encoding="utf-8-sig")  # one string


def test_the_update_window_shows_the_release_and_how_to_get_it(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QLabel

    from bodega.ui.dialogs.update import UpdateDialog

    app = QApplication.instance() or QApplication([])
    d = UpdateDialog(update.parse_release(GITHUB_ANSWER))
    assert "9.1.0" in d.findChild(QLabel, "DialogTitle").text()
    shown = d.notes.toPlainText()
    assert "Faster glitches" in shown and "Download" not in shown
    assert d.btn_go.isHidden() and "GitHub Desktop" in d.status.text()  # from the code: nothing to install
    d.close()
    app.processEvents()


def test_whats_new_is_the_words_without_downloads_or_github_credits():
    generated = (
        "## Download\n| a | b |\n**First launch on Mac:** open it.\n\n"
        "## What's Changed\n"
        "* Start tiles by @nickvenecia in https://github.com/nickvenecia/bodega/pull/7\n"
        "<!-- generated -->\n\n"
        "## New Contributors\n* @nickvenecia made their first contribution in https://x\n\n"
        "**Full Changelog**: https://github.com/nickvenecia/bodega/compare/v1.1.5...v1.1.6"
    )
    assert update.whats_new(generated) == [("heading", "What's Changed"), ("item", "Start tiles")]
    written = "The first one.\n\n## What's New\n\n- A long line\n  carried on.\n1. Two\n\n## Empty\n## Download\n| x |"
    assert update.whats_new(written) == [
        ("text", "The first one."),
        ("heading", "What's New"),
        ("item", "A long line carried on."),
        ("item", "Two"),
    ]
    assert update.whats_new("") == []


def test_release_text_is_never_read_as_html(qapp):
    from bodega.ui.dialogs.update import Notes

    n = Notes([("item", "<b>x</b> **bold** `code` [page](https://example.com/a?b=1&c=2) [run](file:///etc)")])
    page = n.toHtml()
    assert "&lt;b&gt;x&lt;/b&gt;" in page and "bold" in page and "`" not in n.toPlainText()
    assert 'href="https://example.com/a?b=1&amp;c=2"' in page and "file:" not in page
    assert Notes([]).toPlainText() == "No notes came with this version."


def test_release_notes_are_the_changelog_entries():
    import importlib.util

    from bodega import __version__

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("release_notes", root / "scripts" / "release_notes.py")
    rn = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rn)
    log = "# Changelog\n\n## 2.0.1\n\n- Fixed it.\n\n## 2.0.0\n\n- Made it.\n"
    body = rn.notes(log, "v2.0.1")
    assert update.whats_new(body) == [("heading", "What's New"), ("item", "Fixed it.")]
    assert "Bodega-mac-apple-silicon.dmg" in body and "Made it." not in body
    assert (
        update.whats_new(rn.notes(log, "3.0.0")) == []
    )  # no entries: the window says "No notes came with this version."
    assert rn.changes(rn.CHANGELOG.read_text(encoding="utf-8"), __version__)  # this version has its entries


def test_window_offers_the_update(qapp, data_folder):
    from bodega.core.store import Library
    from bodega.ui.window.main_window import MainWindow

    w = MainWindow(Library(data_folder).load())
    rel = update.parse_release(GITHUB_ANSWER)
    w._found_release(rel, quiet=True)
    assert w.sidebar.btn_update.isVisibleTo(w.sidebar) and w.sidebar.btn_update.text() == "Update to 9.1.0"
    w.shutdown()


def test_a_new_version_found_on_opening_shows_right_away(qapp, data_folder, monkeypatch):
    """The automatic check runs every launch; what it finds opens the update window by itself, but never on
    top of another window."""
    from PySide6.QtWidgets import QApplication

    from bodega.core import sample, update
    from bodega.core.store import Library
    from bodega.ui.window.main_window import MainWindow

    win = MainWindow(sample.fill(Library(data_folder).load()))
    win.show()
    shown, later = [], []
    monkeypatch.setattr(win, "show_update", lambda: shown.append(win._release.version))
    monkeypatch.setattr("PySide6.QtCore.QTimer.singleShot", lambda ms, *a: later.append(a[-1]))  # (ms, owner, fn)
    monkeypatch.setattr(QApplication, "activeModalWidget", staticmethod(lambda: object()))
    win._found_release(update.Release("99.0.0"), quiet=True)
    assert not shown and later  # another window is open: it waits
    monkeypatch.setattr(QApplication, "activeModalWidget", staticmethod(lambda: None))
    later.pop()()
    assert shown == ["99.0.0"] and win.sidebar.btn_update.isVisibleTo(win.sidebar)
    win._found_release(update.Release("0.0.1"), quiet=True)  # nothing newer: nothing shows
    assert shown == ["99.0.0"]
    win.close()


def test_a_build_shows_the_commit_it_was_made_from(monkeypatch):
    from bodega import __version__, _build, version_label

    assert version_label() == __version__  # from source: no commit to show
    monkeypatch.setattr(_build, "COMMIT", "a1b2c3d")
    assert version_label() == f"{__version__} (a1b2c3d)"


@pytest.mark.parametrize("kind", ["mac-app", "windows-installed", "windows-portable", "appimage", "linux-folder"])
def test_every_build_can_find_its_own_update_offline(kind, monkeypatch, capsys):
    from bodega import cli

    monkeypatch.setattr(update, "install_kind", lambda: kind)
    assert cli.update_check() == 0
    assert "update check ok" in capsys.readouterr().out
    assert set(cli.ASSETS) >= {n for k in ("windows-installed", "appimage") if (n := update.asset_name(k))}


def test_update_from_a_file_starts_the_swap_a_real_update_would(tmp_path: Path, monkeypatch, capsys):
    """(The standard's T-15) CI updates each packaged build from its own download (cli update-from): this is that
    command, with the install and the helper faked; build.yml then checks the copy was swapped and still runs."""
    from bodega import cli

    assert cli.update_from(str(tmp_path / "x.tar.gz")) == 1  # from its code: no
    assert "update failed" in capsys.readouterr().out
    folder = tmp_path / "Bodega"
    folder.mkdir()
    monkeypatch.setattr(update, "install_kind", lambda: "linux-folder")
    monkeypatch.setattr(update, "target", lambda _kind: folder)
    monkeypatch.setattr(update, "data_dir", lambda: tmp_path / "data")
    started = []
    monkeypatch.setattr(update, "run", started.append)
    wrong = tmp_path / "Bodega-windows-portable.zip"
    wrong.write_bytes(b"zip")
    assert cli.update_from(str(wrong)) == 1 and "isn't the file" in capsys.readouterr().out
    tar = tmp_path / "Bodega-linux-x64.tar.gz"
    with tarfile.open(tar, "w:gz") as t:
        info = tarfile.TarInfo("Bodega/Bodega")
        info.size = 3
        t.addfile(info, io.BytesIO(b"new"))
    assert cli.update_from(str(tar)) == 0 and "update started" in capsys.readouterr().out
    (plan,) = started
    assert plan.script.parent != tmp_path and tar.exists()  # a copy, where a download lands; the file stays
    shutil.rmtree(plan.script.parent)
