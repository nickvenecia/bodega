# Bodega code rules

How Bodega's code is organized and the rules every change follows. The look of the app has its
own rulebook: **[DESIGN.md](DESIGN.md)**. Read both before changing anything.

---

## 1. Where things go

```
bodega/
  core/        Gear, packages, rentals: data, money, dates, pricing, importing, saving. No Qt imports — ever.
  doc/         Drawing the pages (QtGui only, no widgets): fonts, layout, PDF/PNG/print.
  services/    Outside Bodega (the keychain, AI providers, Saldo, accounts, feedback). No Qt.
  ui/          Everything you see. Qt Widgets. Talks to core/, doc/ and services/, never the other way round.
  app.py       Starts the window (fonts, stylesheet, one window at a time, --smoke-test)
  cli.py       Same drawing without a window: `python -m bodega cli ...`
tests/         One test file per area (test_pricing.py, test_store.py, test_documents.py, test_window.py…)
scripts/       make_icon.py, release_notes.py (a Release's text, from CHANGELOG.md)
packaging/     Installer files per OS
```

- `core/` must work headless and be testable without Qt.
- Per-user files (gear, rentals, logos, logs) go under `core.paths.data_dir()`.
  Never write next to the app, and never into a fixed name in the shared temp folder.
- Exported files go where the person picks (default Documents/Bodega), written to a temp file beside the
  target and moved into place.

---

## 2. Style

- Python 3.12. `from __future__ import annotations` at the top of every module.
- **Ruff** formats and lints. Before every commit:
  ```bash
  ruff format . && ruff check . && mypy && python -m pytest -q
  ```
  CI fails if any of the three fails. Settings are in `pyproject.toml` (line length 120, the standard's).
- Type hints on every function signature. Prefer `X | None` and built-in generics (`list[str]`).
- Names: `snake_case` functions/variables, `PascalCase` classes, `UPPER_CASE` constants,
  `_leading_underscore` for anything private to a module.
- Every module starts with a one-line docstring saying what it's for. Public functions get a
  docstring when the name doesn't say everything.
- Comments explain **why**, not what. Link to the bug or quirk when a line looks odd.
- No dead code, no commented-out code, no `print()` in the app (use the logger).

---

## 3. Safety rules (never break these)

**The user's files**
1. **Never lose gear or a rental.** All saving goes through `store.write_json`: a temp file in the same folder,
   then `os.replace`. A file that can't be read is renamed aside (`.unreadable-<time>`), never deleted.
2. Exports (PDF, PNG) are the same: temp file beside the target, then `os.replace`. A failed export
   never leaves a broken file or replaces a good one.
3. Logos are copied into the data folder; the original is never touched.

**Running other programs**
4. Always pass arguments as a **list**. Never `shell=True`, never build a command string.
5. Every `subprocess` call gets `**fileutil.popen_kwargs()` (no console windows on Windows).
6. Never wait on a program's output with a pipe nobody reads (a full pipe freezes it).
7. The only programs Bodega starts are the system's own (open / explorer / xdg-open to show a file, and
   the updater's helper script).

**Network**
8. HTTPS only, with certificate checks on (`net.ssl_context()`; never `verify=False` or `CERT_NONE`).
9. Bodega goes online only for what the person asks for: the update check and download (GitHub), a Google
   Sheet they import, a link they ask about (Check Price, Update from Links, a photo from a link) and their own AI
   provider. Every link goes through `core/web.py`; SECURITY.md lists what each one receives. Updates are checked
   against the **SHA-256 GitHub publishes** before they're used. Rentals and renters are never sent anywhere.
10. Pin build-time downloads to official sources with checksums (appimagetool in build_appimage.sh).

**Input from outside**
11. Treat file names, logo files and anything from another process as untrusted.
    The single-instance socket only accepts the same user (`UserAccessOption`) and only ever raises the window.
12. Never `eval`/`exec`/`pickle` anything. Settings are JSON.
13. Never log or show secrets or full environment variables.

**Errors**
14. No silent `except: pass` around real work. Catch the narrowest exception you can; if you must
    swallow one, `log.warning(..., exc_info=True)` so it lands in the log file.
15. Messages shown to the user are plain English and say what to do next (see DESIGN.md §7).
    Technical details go to the log (`core/log.py`, `bodega.log` in the data folder).

**The window**
16. Anything a refresh can rebuild (start tiles, the sidebar's rows, line items) acts once its click is over
    (`QTimer.singleShot(0, self, …)`, `DetailsBase.later`, `LineEditor._later`), never inside it. Its click may
    open a window or a menu, and whatever that window throws away is gone before the click is over: if it's the
    very thing that was clicked, Bodega crashes (on a Mac, every time). `still_there_after` in
    `tests/test_window.py` catches it.
17. A part of a window that's thrown away while the window stays open is hidden first, then `deleteLater()`
    (Settings' `_fill`). Destroyed while it still shows with the focus in it (on a Mac, the field you just typed
    in), a form takes Bodega down with it.
18. A dialog Bodega opens on top is let go once it closes (app.py `_RoundPopups._lets_go`), so read what you
    need from it as soon as `exec()` returns and never keep one to show again: make a new one.
    `tests/test_memory.py` opens and closes every screen and fails if anything stays behind.
19. A delayed call names what it belongs to: `QTimer.singleShot(ms, owner, fn)`, never `(ms, fn)`. If the owner is
    gone first (a window closed and deleted), Qt drops the call instead of running it on something that's no longer
    there; on a Mac that once crashed the next window. `tests/test_code_rules.py` checks every call.
20. Python's cycle collector is off and runs on the window's thread between events (app.py `_MainThreadGC`):
    never turn it back on, and never call `gc.collect()` from a background job. Left to itself it runs on any
    thread, in the middle of Qt's own work, and freeing a Qt object there crashes Bodega at random.

---

## 4. Threads

- Anything that waits on the internet or may take more than a moment runs off the main thread and talks to the
  window with **signals**, almost always through `ui/components/worker.py` (`Worker`, with progress and Stop).
  Today that's:
  - the Assistant's jobs and questions (`ui/window/ai.py`, `ui/panels/assistant.py`) and the list of models in AI
    Settings (`ui/dialogs/ai_setup.py`);
  - photos from links: one piece's (`ui/panels/item.py`) and every piece's (`ui/window/transfer.py`);
  - opening a Google Sheet, backing up and restoring (`_run_transfer` in `ui/window/transfer.py`, one at a time);
  - Check Price (`PriceCheck` in `ui/panels/item.py`);
  - the update check and download (`ui/dialogs/update.py`).
- A result that comes back late checks the window still shows what it was for (the same piece, still open) before
  it touches anything. Quitting while one runs asks first (Stop and Quit), and waits for it at most QUIT_WAIT_MS.
- Drawing a page takes milliseconds; keep it that way.

---

## 5. Speed

- The preview is redrawn DRAW_DELAY_MS after the last change, and saving waits SAVE_DELAY_MS, so typing never stutters.
- Font metrics are cached (`doc.fonts.metrics`); icons are cached (`theme.icon`).

---

## 6. Tests

- Every change to `core/` or `doc/` comes with a test. Name it after the behavior, as a sentence:
  `test_a_broken_file_is_set_aside_not_lost`.
- A fix comes with a test that fails on the code before the fix: run it once without the fix and see it fail.
- Never skip, disable or loosen a test to get green.
- Tests never touch real data: `tests/conftest.py` gives every test its own empty data folder.
- A warning from Qt fails the test it came in. A test that hands Qt a broken file on purpose is marked
  `@pytest.mark.qt_warnings`. The offscreen screen's own limits ("This plugin does not support…") are let through.
- Wait for what you're waiting on (`wait_for(done)` in `tests/test_window.py`), never a fixed time.
- A document's PDF is read back with an independent reader (pypdf): its words are real text.
- UI changes: check screenshots (`QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR`).
- Before a release, the packaged app must pass `--smoke-test` (CI does this on every platform).

---

## 7. Commits and releases

- One topic per commit. Message: short summary line in the present tense ("Add A4 paper"),
  then a blank line and the why, if it isn't obvious.
- Anything a user would notice goes in `CHANGELOG.md` under the next version, and the same pull request bumps
  `__version__` in `bodega/__init__.py` (the last number for fixes and polish, the middle one for a new feature).
- Merging is releasing: when main has a version with no tag yet, CI builds, tags it `vX.Y.Z` and publishes the
  downloads. A pull request that doesn't bump the version (docs, tests, tidying) releases nothing.
- Never commit `build/`, `dist/`, real gear lists, rentals, personal details, or anything with a password or key in it.
  Signing secrets live only in GitHub → Settings → Secrets.
