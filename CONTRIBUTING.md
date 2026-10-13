# Bodega code rules

How Bodega's code is organized and the rules every change follows. The look of the app has its
own rulebook: **[DESIGN.md](DESIGN.md)**. Read both before changing anything.

---

## 1. Where things go

```
bodega/
  core/        Gear, packages, rentals: data, money, dates, pricing, importing, saving. No Qt imports — ever.
  doc/         Drawing the pages (QtGui only, no widgets): fonts, layout, PDF/PNG/print.
  ui/          Everything you see. Qt Widgets. Talks to core/ and doc/, never the other way round.
  app.py       Starts the window (fonts, stylesheet, one window at a time, --smoke-test)
  cli.py       Same drawing without a window: `python -m bodega cli ...`
tests/         One test file per area (test_money.py, test_store.py, test_render.py, test_window.py…)
scripts/       make_icon.py, make_fonts.py, release_notes.py (a Release's text, from CHANGELOG.md)
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
  ruff format . && ruff check . && python -m pytest -q
  ```
  CI fails if any of the three fails. Settings are in `pyproject.toml` (line length 110).
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
9. The only network use is the update check and download (GitHub). Updates are checked against the
   **SHA-256 GitHub publishes** before they're used. Gear lists and rentals are never sent anywhere.
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

---

## 4. Threads

- Everything runs on the main thread except the update check and download (`ui/update_dialog.py`),
  which talk to the window with **signals**. Drawing a page takes milliseconds; keep it that way.

---

## 5. Speed

- The preview is redrawn DRAW_DELAY_MS after the last change, and saving waits SAVE_DELAY_MS, so typing never stutters.
- Font metrics are cached (`doc.fonts.metrics`); icons are cached (`theme.icon`).

---

## 6. Tests

- Every change to `core/` or `doc/` comes with a test. Name it after the behavior:
  `test_a_broken_file_is_set_aside_not_lost`.
- Tests never touch real data: `tests/conftest.py` gives every test its own empty data folder.
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
