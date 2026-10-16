# Session Log

What's been done to Bodega, session by session, and what each taught. `CHANGELOG.md` is only what people using
Bodega will notice (it becomes the release notes and the update window), so this lives here
([PROJECT_ADDENDUM.md](PROJECT_ADDENDUM.md), §18.3: proposed, waiting for the owner's yes, G-03).

## Start here

- **State**: version 1.3.0, on this work's branch, not merged yet (main is 1.2.1). Merging it releases 1.3.0: CI tags it and publishes the six downloads. CI hasn't run on this branch yet (it runs on main, on
  pull requests, or by hand): open the pull request, or run "Build Bodega" by hand on the branch, before merging.
- **Checks, with what they should say**:
  - `ruff format . && ruff check . && mypy && python -m pytest -q`: no changes, no problems, "Success: no issues
    found", every test passes (421 test functions, some run in several cases; the run ends without pytest's summary
    line by design, so read its exit code).
  - `QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR`: 22 pictures of every screen (add `BODEGA_LOOK=dark`,
    `BODEGA_ACCENT=yellow`, `BODEGA_SIZE=1280x700`; for 1280 or wider, give Qt a big test screen:
    `QT_QPA_PLATFORM="offscreen:configfile=screen.json"`, as `tests/test_sizes.py` does).
  - `python -m bodega cli update-check`: says which release this copy would update to, offline.
- **Next**: the owner's answers (questions 8 to 30 in [STANDARD_AUDIT.md](STANDARD_AUDIT.md)), then what's left in
  its "After the fixes": 21 partly done, 23 larger redesigns.
- **Quirks**:
  - Qt's offscreen test screen is only 800 points wide, under Bodega's 1280 minimum: anything measured wider runs in
    its own process with a configured screen (`tests/test_sizes.py`). A screenshot narrower than 1280 cuts the
    totals row; that's the test screen, not Bodega.
  - A warning from Qt fails the test it came in; the offscreen screen's own ("This plugin does not support …") are
    let through (`tests/conftest.py`). A test that feeds Qt a broken file on purpose is marked `qt_warnings`.
  - Tests leave with `os._exit` once pytest has its result, because Qt objects can crash while Python shuts down on
    Windows (T-09, still open).
  - Every test starts with a fresh AI meter with no per-minute wait (`tests/conftest.py`, `fresh_ai_meter`).
  - A dialog is deleted once it closes (`app.py`, `_lets_go`): read what you need from it as soon as `exec()`
    returns. `tests/test_memory.py` opens and closes every screen and fails if anything stays behind.
  - The standard itself is kept out of the repository (`.git/info/exclude`): a fresh clone needs the owner's copy at
    `docs/UNIVERSAL_APP_STANDARD.md`.
- **How it ships**: bump `__version__` in `bodega/__init__.py` with the CHANGELOG entries; merging to main is the
  release (CI builds, tags `vX.Y.Z`, publishes). The download names are a contract (README, update.asset_name).
- **What only the owner can supply**: an Apple Developer ID and a Windows code-signing certificate (S-23); branch
  protection on main (O-01); the answers to the questions in the audit.

## 2026-10-16: the standard, applied

**Changed** (119 small commits, each with its tests; what people will notice is in CHANGELOG 1.3.0, and
`git log main..` on the branch lists them all):

- **Money, numbers and records (S1)**: a rental's prices hold once it's booked; a rental number is never given
  twice, with a Next Number per profile; booked rentals are cancelled and gear on rentals retired instead of
  deleted; booking over a shortage asks first; each rental keeps its history; Send to Saldo replaces Send to Cobro.
- **Never losing work (S1)**: a failed save is said until it works and asked about before quitting; forms ask
  before dropping typing; safety copies every day and before big changes, with Restore; files are read defensively
  (a newer Bodega's fields kept, a format version); Check Out and Check In keep each tick as it's made.
- **AI (S1)**: every answer and every job capped, gear lists marked as data, what's sent said plainly; every
  question counted, with a daily limit (300, warning at 80%) and 20 a minute; the key checks itself; models by name.
- **Look and feel**: tokens and shared components to Appendices A and G (type, sizes, radii, colours at 4.5:1,
  buttons, fields, menus, sidebar, tables, segments, switches, date fields with a month popover, a record pager,
  Search Everything); Reduce Motion, Increase Contrast and Reduce Transparency followed; focus rings and screen-reader
  names everywhere, the calendar included; plain words, one word for each thing.
- **Speed and memory**: fast at 3,000 pieces and 2,000 rentals (opening, refreshing, deleting, approving changes,
  undo), with every big job timed in `tests/test_scale.py`; closed windows let go (they piled up all day).
- **Structure**: one store operation per change; rules asked of the record (`Rental.is_over()`, `Item.can_rent()`)
  with a test that no status word is compared in a screen; one table of settings, of places and of pages; the parts
  with no Qt type-checked in CI.

**Decided** (by the owner): a rental's prices hold once it's booked; a rental number is never given twice (a Next
Number setting carries a series on); booked, out and returned rentals are cancelled, only quotes are deleted, and
gear on rentals is retired; booking over a shortage asks first; import blanks are explained and safe, and the
sheet's pricing starts off once you have a profile; Send to Cobro became Send to Saldo; nothing mentions AI or the
tools used to build Bodega in commits or documents.
**Decided** (as the standard has it, the owner having said "whatever is industry standard"): prices lock at
booking; numbers are never reissued; the standard's AI limits (20 a minute) with a daily limit of Bodega's own
(300); today on the calendar marked by its number, not a filled accent circle (G.22); the record pager floats at
the foot of the side panel.

**Open**: 21 checks partly done and 23 larger redesigns ([STANDARD_AUDIT.md](STANDARD_AUDIT.md), "After the
fixes"): among them text that follows the system's text size (V-16), ticks and a selection bar on the gear list
(C-37, C-73), attached gear folding under its piece (C-108), print options (C-53, C-61), one command table for every
menu (D-04). 26 wait on the owner (questions 8 to 30, and the departures proposed in PROJECT_ADDENDUM.md).

**For the Standard** (general lessons, for the owner's standard):

- **Two orders for one palette.** §4.8 says a command palette lists commands first, then places, then records; G.23
  says places first, then records, then commands. Bodega follows G.23 (the detailed spec). Pick one.
- **Read a component's main-text rule before its Appendix G row.** §14.10 says Clear Chat is a trash icon because a
  compose icon "was not found as the way to clear"; the first version here used a compose icon, built from the
  table alone. A one-line pointer from each G table to its rule in the main text would have caught it.
- **An independent PDF reader finds what a size check can't.** Reading the agreement back with pypdf showed that
  the rental number and phone brackets came out of every PDF as private symbols: the type's contextual alternates
  have no letters behind them. Worth a line in §10 or §17: turn contextual alternates off for documents, and test a
  PDF's text, not only its size.
- **"Toolkit warnings fail the run" needs a short allowlist.** The offscreen test platform warns about things it
  can't do ("does not support raise()"); everything else is a real bug. The standard could name the pattern.
- **Where the record pager floats in a split view.** §3.5 puts it at "the bottom centre of the content"; with records
  in a side panel the record is the panel, not the list. The standard could say so for inspectors.
- **Text size up to 200% and fixed control sizes.** §2.7 asks for 200% text with layouts that stack, while Appendix A
  fixes controls at 28 and rows at 44 on a computer. On a desktop toolkit that is a redesign of every fixed height,
  not a setting. The standard could say how the two meet on a pointer computer, and what "the system's text size"
  means on macOS and Windows, where apps aren't told.
- **A form's Return and a dialog's default button.** "Return moves to the next field, and on the last one confirms"
  fights every toolkit's default-button behaviour. Worth naming as a known trap, with the fix.
- **Marking one menu item red.** Qt's stylesheets can't select one action; Bodega marks it as the menu's "default"
  and styles that red. Per-toolkit notes would save the next app the search.
- **Keys shown in words come from the shortcut.** A hand-typed "(⌘J)" showed ⌘ on Windows. The standard could say:
  every key written in a tooltip or a label is read from the command, in the platform's own symbols.
- **The cheapest memory test counts live UI objects.** Opening and closing every screen three times and counting
  widgets found a window that stayed in memory each time it closed (2,000 widgets a round); T-06 could name it as
  the first memory check, before profiling bytes.
- **Measure every instance, not the named ones.** A test of "every circle is square and at its size" found the
  filter button at 28 beside 36s, which a list of named controls had missed.
- **Profile at production size.** At 3,000 pieces, one save per approved change cost 2 seconds and deleting 300
  pieces cost 3 (a lookup without its index); §7 could add "a batch saves once" and "time every bulk action at the
  largest size you promise".
- **A rule kept in one place needs a guard.** A test that fails when a screen compares a status word itself
  (`.status == "out"`) keeps §8.2's "rules live in one module" true after the refactor.
- **Rate limits when the person pays.** §14.6's 20 requests a minute is written for a server; for a desktop app on
  the person's own key it mostly slows big jobs. The standard could say whether it applies to bring-your-own-key.
- **A wall calendar's today.** G.22 sets today in the date picker (accent words, Semibold); a month or week view of
  bookings isn't specified, and Apple's Calendar uses a filled circle. Worth a row.
