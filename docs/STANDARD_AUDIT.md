# Standard Audit: Bodega

Every check in Part 19 of the owner's Universal App Standard (version 1.5), run against Bodega. Each is Pass, Fail
(what to change, and where) or N/A (why). A check passes only if it holds everywhere in the app. What Bodega may do
differently is in [PROJECT_ADDENDUM.md](PROJECT_ADDENDUM.md); until the owner says yes to a departure there, its
check stays a Fail here.

```
App:                       Bodega                Version / commit: 1.2.2 · 665289e (a branch;
                                                                    main is 1.2.1 at dcf7eca)
Audited by:                review session        Date: 2026-10-16
Sizes and appearances checked: computer 1280 × 900, 1440 × 900, 2200 × 1000 and the smallest window 1280 × 700 ·
                               light and dark · every accent's contrast computed (Yellow the palest) ·
                               phone and tablet: N/A (no such layout; the window is never narrower than 1280)
```

**How it was measured.** The real window, offscreen (Qt's offscreen platform, the made-up Juniper Lane Films sample in a
throwaway folder): every visible control's height, every table and menu row, icon and type sizes, whether each circle
is square, left and right edges at three widths, layout margins off the 4-point grid, and contrast computed from the
tokens. Screens looked at in light and dark: All Gear with a piece open, a rental, a kit, the calendar, the assistant,
Settings (General, Profiles, AI), a menu, an alert, the empty first launch. Behaviour was probed with small scripts
(a failed save, a deleted rental's number, a returned rental after a rate change, Ctrl+Backspace in a field, files
with odd values), and the rest read from the code, the tests, the workflows and the git history. The whole test suite
passes (210 tests); nothing in the app was changed for the audit.

**Reading it.** S1 is critical (data, money, security, cost: fix before the next release), S2 major (broken
behaviour, accessibility, inconsistency people notice), S3 minor (polish and words). Many N/A rows are the standard's
server, organization, sign-in, phone and stock checks: Bodega is one person's desktop app with local files.

## Summary

**Pass 111 · Fail 253 (S1 39 · S2 135 · S3 79) · N/A 157** of 521 checks.

Since then (see [After the fixes](#after-the-fixes)): of the 253 failures, **220 fixed, 4 partly, 9 not
started (larger redesigns), 19 waiting on the owner, and 1 no longer applies** (a web page's rule).

| Section | Checks | Pass | Fail | S1 | S2 | S3 | N/A |
|---|---|---|---|---|---|---|---|
| 19.1 Foundations and look (V) | 43 | 14 | 25 | 0 | 10 | 15 | 4 |
| 19.2 Structure and navigation (N) | 28 | 8 | 9 | 0 | 7 | 2 | 11 |
| 19.3 Components and patterns (C) | 170 | 43 | 66 | 3 | 40 | 23 | 61 |
| 19.4 Words (W) | 22 | 3 | 19 | 0 | 8 | 11 | 0 |
| 19.5 Interaction (I) | 31 | 3 | 25 | 2 | 18 | 5 | 3 |
| 19.5 Accessibility (A) | 13 | 1 | 10 | 0 | 9 | 1 | 2 |
| 19.6 Architecture (D) | 51 | 6 | 29 | 11 | 10 | 8 | 16 |
| 19.6 Data integrity (K) | 19 | 1 | 8 | 4 | 4 | 0 | 10 |
| 19.7 Performance and scale (P) | 16 | 0 | 8 | 0 | 5 | 3 | 8 |
| 19.8 Security (S) | 37 | 9 | 5 | 4 | 1 | 0 | 23 |
| 19.9 Abuse and cost (X) | 12 | 1 | 3 | 3 | 0 | 0 | 8 |
| 19.10 AI (AI) | 32 | 7 | 20 | 6 | 7 | 7 | 5 |
| 19.11 Privacy (R) | 9 | 6 | 3 | 2 | 1 | 0 | 0 |
| 19.12 Reliability (O) | 15 | 4 | 6 | 4 | 2 | 0 | 5 |
| 19.12 Testing (T) | 18 | 4 | 13 | 0 | 11 | 2 | 1 |
| 19.12 Process (G) | 5 | 1 | 4 | 0 | 2 | 2 | 0 |
| **All** | **521** | **111** | **253** | **39** | **135** | **79** | **157** |

## After the fixes

Checked again on 2026-10-16 at version 1.3.0 (before it's merged), with every one of the 253
failures above looked at in the code and its tests by five read-only reviews, and the ones fixed since then checked
the same way. "Fixed" means the code does what the check asks and a test holds it there; "Partly" says what's left;
"Not started" are the larger redesigns; the owner's items wait on a question below or a departure in
[PROJECT_ADDENDUM.md](PROJECT_ADDENDUM.md). Nothing is marked fixed by skipping or loosening a test.

**Of the 253 failures: Fixed 220 · Partly 4 · Open 9 · Waiting on the owner 19 · No longer applies 1.**

### Partly: what's left

| Check | Sev | What's left |
|---|---|---|
| A-07 | S2 | Text sizes are fixed, so the system's text size and Bold Text aren't followed (with V-16). |
| C-90 | S3 | The profile form is sized by kind; the side panels' fields still stretch to the panel's width. |
| N-18 | S2 | A renter opens in a sheet over the window now; editing one in place needs a Renters page of its own (a list and a panel), not built yet. |
| T-04 | S2 | Tests still reach some controls through private names (about 48 in test_window.py). |

### Not started: the larger redesigns

| Check | Sev | What it needs |
|---|---|---|
| C-25 | S2 | Import and Review are wide windows; the standard wants them as pages. |
| C-53 | S2 | The print window has no column ticks or order, no letterhead options, no presets. |
| C-55 | S3 | The table is drawn straight on the page, not in a card. |
| C-61 | S2 | The print window has no filter cards (column, from, to). |
| C-120 | S3 | Settings › General is sections, not grouped rows in cards; Profiles is one long form. |
| I-09 | S3 | Scroll bars are drawn by Bodega's stylesheet, not the system's own. |
| I-18 | S3 | Hover changes a fill only, with no lift. |
| T-13 | S3 | Tests find controls by their code names, not by role and visible words. |
| V-16 | S2 | Text sizes are fixed points: nothing follows the system's text size, no 200% check (a layout pass). |

### Waiting on the owner

| Check | Sev | Decided by |
|---|---|---|
| AI-13 | S1 | a key stored as the repository secret BODEGA_EVAL_KEY: the evaluation (services/ai/evals.py) then runs on every change |
| AI-18 | S3 | what files the assistant would take (a spreadsheet to import, a photo to name a piece: photos cost more and go to your provider); the standard says build no door to a room that isn't built |
| AI-28 | S2 | question 15 |
| C-129 | S2 | question 8 |
| D-08 | S1 | the whole-dollar lists in PROJECT_ADDENDUM.md |
| D-20 | S3 | question 13 |
| D-22 | S2 | question 7 |
| D-37 | S1 | question 9 |
| G-03 | S3 | the session log (docs/SESSION_LOG.md), a proposed departure |
| G-05 | S3 | question 30 |
| O-01 | S1 | question 26: branch protection (the type check of core/ and services/ now runs in CI) |
| R-03 | S1 | question 14 |
| S-16 | S1 | the updater's helper script in PROJECT_ADDENDUM.md |
| S-23 | S1 | question 27: later, by the owner's choice (not wanted yet) |
| V-22 | S3 | the accent in PROJECT_ADDENDUM.md |
| V-28 | S3 | the accent in PROJECT_ADDENDUM.md |
| V-42 | S3 | a proposed departure: line heights stay the font's own (within 2 points of A.4); exact ones need formatted labels, which Bodega avoids so names and AI words never become formatting |
| W-05 | S3 | question 20 |
| W-08 | S3 | question 20 |

### No longer applies

| Check | Sev | Why |
|---|---|---|
| A-02 | S2 | Reflow at 320 points is a web page's rule; Bodega is a desktop app (the owner, 2026-10-16). |

### Fixed

- **A**: A-01, A-03, A-05, A-06, A-10, A-11, A-12, A-13
- **AI**: AI-01, AI-03, AI-07, AI-08, AI-09, AI-11, AI-14, AI-15, AI-16, AI-17, AI-19, AI-20, AI-23, AI-24, AI-29, AI-30, AI-31
- **C**: C-01, C-03, C-04, C-06, C-08, C-11, C-12, C-13, C-16, C-17, C-19, C-21, C-23, C-24, C-26, C-27, C-28, C-29, C-31, C-32, C-34, C-37, C-38, C-39, C-42, C-44, C-45, C-47, C-49, C-50, C-51, C-54, C-58, C-59, C-65, C-66, C-67, C-69, C-70, C-72, C-73, C-76, C-82, C-88, C-100, C-105, C-106, C-108, C-111, C-114, C-117, C-119, C-138, C-144, C-160, C-163, C-164, C-167, C-168
- **D**: D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-10, D-11, D-12, D-15, D-16, D-18, D-21, D-23, D-24, D-25, D-26, D-31, D-32, D-34, D-41, D-42, D-49, D-51
- **G**: G-01, G-02
- **I**: I-01, I-02, I-03, I-04, I-06, I-07, I-08, I-10, I-11, I-12, I-13, I-14, I-15, I-19, I-20, I-21, I-23, I-24, I-25, I-26, I-29, I-30, I-31
- **K**: K-02, K-03, K-04, K-06, K-07, K-09, K-10, K-12
- **N**: N-01, N-02, N-03, N-04, N-05, N-06, N-15, N-17
- **O**: O-04, O-05, O-07, O-09, O-11
- **P**: P-01, P-02, P-03, P-04, P-09, P-13, P-15, P-16
- **R**: R-01, R-05
- **S**: S-17, S-21, S-25
- **T**: T-01, T-03, T-05, T-06, T-09, T-11, T-12, T-14, T-15, T-16, T-18
- **V**: V-04, V-08, V-09, V-11, V-13, V-14, V-15, V-17, V-18, V-19, V-23, V-24, V-25, V-26, V-32, V-33, V-35, V-36, V-37, V-40, V-41
- **W**: W-02, W-03, W-04, W-06, W-09, W-10, W-11, W-12, W-14, W-15, W-16, W-17, W-18, W-19, W-20, W-21, W-22
- **X**: X-01, X-06, X-08

## The top ten fixes

In the order the standard asks for (S1 first). Items marked **ask first** change how the business works (numbers,
money, deleting), so they wait for the owner's answer below.

1. **A finished rental's price can change after the fact** (K-12, S1, **ask first**). Lines without a typed rate are
   priced from today's day rates, so editing a piece's rate rewrites rentals that are already out or returned.
   Verified: a returned rental went from $1,802.00 to $5,694.00 after one piece's day rate changed. Lock a rental's
   prices once it is booked or goes out (the owner decides which), as it already keeps its own copy of the renter.
2. **Rental numbers can repeat** (C-51, C-144, D-07, D-24, I-29, C-66; S1, **ask first**). The next number is the
   highest in use plus one, so deleting the newest rental hands its number to the next renter; typed numbers are never
   checked for a clash; there's no Next Number setting to carry a series on. Never issue a number twice, and say a
   clash in the field.
3. **A failed save is easy to miss, and quitting then loses the work** (C-31, K-06, I-07; S1). A save that fails
   (disk full, folder gone) shows a toast for a few seconds; quitting afterwards closed the window and lost the edit
   (verified). The profile, renter, feedback and check-in windows also drop typing on Cancel or Esc without asking.
   Keep a lasting "Not saved" banner while the problem lasts, refuse to quit silently over unsaved work, and ask
   before discarding typing.
4. **No automatic safety copy, and Back Up has no Restore** (D-18, O-07; S1). Rentals, kits, renters and profiles are
   overwritten with no previous copy (only gear.json is snapshotted, and only before AI changes); a backup zip can't
   be put back from inside Bodega. Keep a last good copy of each file and add Restore… with a test.
5. **Files are read too trustingly** (D-06, D-12, O-04, D-11; S1). One unexpected value in a data file stops Bodega
   from opening (verified: a kit named with a number); fields written by a newer Bodega are dropped on the next save;
   an unknown rental status reads as Quote, which frees its gear. Read every record defensively, keep unknown fields,
   read an unknown status as the cautious one, and give the files a format version.
6. **Send to Cobro sends invoices where they're no longer read** (D-16, D-32, K-02; S2/S1). Cobro is now Saldo, which
   moves Cobro's folder over once and then reads only "Saldo"; Bodega still writes into "Cobro", so drafts sent after
   the switch never appear. Point it at Saldo's folder and name it Send to Saldo; remember which invoice a rental
   became, so a second send updates it instead of making a duplicate.
7. **AI spend and honesty** (X-01, X-08, AI-07, AI-08, AI-09, AI-03, AI-31; S1). Only Anthropic answers are capped in
   length (nine other providers send no cap), a job has no ceiling on calls and keeps calling after repeated failures,
   and the setup says "gear names and links" when each request sends up to 600 pieces with what each cost. Cap every
   provider, bound and stop a job, mark the gear list as data in every prompt, and say plainly what goes out.
8. **Imports guess and overwrite without asking** (I-24, I-26; S1, **ask first**). A blank quantity becomes 1, a blank
   "rent?" becomes yes, a company is guessed, and "Use the Sheet's Pricing" starts on and replaces the profile's
   pricing. Ask what a blank means, and never overwrite curated settings by default.
9. **Untrusted files** (S-17, X-06; S1). SVG logos are kept exactly as they came, and Qt's SVG reader pulls in a
   local picture by path, so a hostile logo can print a file from the computer onto agreements; a CSV cell over
   131,072 characters fails the import with no message. Turn SVG logos into PNG when added, cap sheet sizes, and catch
   the error in plain words.
10. **Keyboard and screen readers** (I-02, I-01, A-10, C-03, A-05, A-06, V-13; S2). Ctrl+Backspace (⌘⌫ on a Mac) is
    bound to Delete…, so pressing it while typing a word away opened "Delete Sony FX6 Cinema Camera (Body Only)?" and
    Return would delete the piece (verified); one stylesheet line (`* { outline: none; }`) removes every focus ring;
    no control has an accessible name; faint text measures 2.57:1. Give Delete a key that never fires while typing,
    bring the focus rings back, name every icon button, and lift faint text to at least 4.5:1.

**Then, in the standard's order:** the release pipeline's gates (O-01: protect main so a PR merges only on green, drop
the Windows installer's `continue-on-error`, add type and dependency checks); signing (S-23, needs an Apple Developer
ID and a Windows certificate); one entry point for every change to data (D-02); and the **foundations**, so later
fixes inherit them: tokens to Appendix A (V-13 contrast, V-14 Apple's text styles, V-17 control 28 · row 44 ·
choice row 32 · bar 36, V-18 the radius scale, V-24 no literals), then the shared components to Appendix G.

## Failures, most severe first

| ID | Sev | Where | What to change |
|---|---|---|---|
| C-31 | S1 | ui/window/editing.py flush (`except OSError` → toast) | A failed save shows a toast that leaves after a few seconds, then nothing: no lasting "Not saved" state or banner while the problem lasts. |
| C-51 | S1 | core/store.py next_number | Deleting the latest rental frees its number: the next rental is given it again (`max(used) + 1`). A number printed on an agreement can come back on another renter's. |
| C-144 | S1 | core/store.py next_number | See C-51: the next number follows the highest in use, so the highest one deleted is issued again. (Typed numbers outside the series don't move it: pass.) |
| I-07 | S1 | ui/dialogs/profile.py:239-244; ui/dialogs/settings.py:219-223; ui/dialogs/client.py:58-66; ui/dialogs/feedback.py:49-51; ui/dialogs/checklist.py:131 | Gear, kits and rentals autosave consistently, with undo (a sound departure). But the explicit-save forms never ask about unsaved changes: profile edits, a new renter, a typed feedback message and check-in ticks are all dropped silently by Cancel, Esc, closing Settings or picking another profile in Settings. Add a Discard Changes / Keep Editing question to these forms. |
| I-24 | S1 | core/importer.py:534,537,561; ui/window/transfer.py:123-131; ui/dialogs/import_sheet.py:98 | Pieces already in Bodega are matched by name and department (there are no item codes) and skipped, which is good. But things the file lacks are guessed: Company is guessed silently from the name, a blank quantity becomes 1 and a blank "Rent?" becomes yes. Existing pieces get the sheet's links without being shown. "Use the Sheet's Pricing" is on by default and overwrites the profile's pricing. Show these and ask. |
| D-02 | S1 | bodega/ui/window/editing.py:200-240, groups.py, transfer.py, pages.py:239 | The screens make the changes themselves: 48 direct Library writes from 10 UI files, with fields set in the UI (attaching sets parent and group at editing.py:222 and skips the department CLAUDE.md promises). Give each operation (attach, book, mark out/returned, delete a rental, send to Cobro, import) one core function that checks, saves atomically, stamps `updated` and records it, and have the screens, the importer and the assistant all call that. |
| D-06 | S1 | bodega/core/model.py:175-181 | Every record is read through `from_dict` with its types fixed, except kits: a kit's name and notes aren't, so a packages.json with a number for a name stops Bodega from opening (verified: AttributeError while building the window). Fix every field in every `from_dict` through one shared reader, test each record with wrong-typed values, and do the same for Cobro's files (cobro.py:134 `int()`). |
| D-07 | S1 | bodega/core/store.py:535-555, 584-590 | Internal ids are random and hidden (uuid4, credit). But the next rental number is "highest in use + 1", so deleting the newest rental gives its number to the next one (verified: JLF-2026-001 deleted, the next rental is JLF-2026-001 again), and a quote's number changes when its year or profile changes. Keep a counter per profile and year that only goes up, and keep deleted numbers spent. |
| D-08 | S1 | bodega/core/money.py:37-74; ui/window/tables.py:899-927, 1006-1008 | The arithmetic passes: exact Decimal, one half-up rounding to the cent (`money.cents`), never float, so totals are right. The check fails on display and sorting: lists and panels show amounts through a second formatter that drops the cents (`fmt_short`, and `whole` rounds value to dollars), and table sort keys are `float(Decimal)`. Use `money.fmt` everywhere (or record whole-dollar day rates in the Addendum) and sort by the Decimal. |
| D-11 | S1 | bodega/core/store.py:231-250; core/model.py | New fields are only ever added, with "off" defaults, and `from_dict` reads older files (credit). But no file carries a version, so there's no upgrade path for a renamed field and no way to tell that a file came from a newer Bodega. Write a version into each file and upgrade one step at a time in `from_dict`, with a test per step. |
| D-12 | S1 | bodega/core/model.py:42-44, 114-115, 178-179, 345-346 | Unreadable files are set aside, never deleted (credit). But fields Bodega doesn't know are dropped on the next save (verified), an unknown rental status reads as Quote (which frees its gear for double-booking), an unknown gear status as Ready and an unknown kit pricing as 15% off. Keep unknown fields when saving, and read an unknown status as the cautious one (the rental holds its gear; the piece is not available). |
| D-15 | S1 | bodega/ui/window/editing.py:442-462; core/store.py:584 | With one person there's no actor to stamp, but nothing records the important changes either: booking, marking out or returned, renumbering and deleting a rental leave no history. All that exists is `checked_out`/`checked_in`, overwritten each time, and an undo list kept in memory. Add an append-only history to each rental and show it on the rental. |
| D-18 | S1 | bodega/core/store.py:56-71, 212-229 | Writes are atomic (temp file, fsync, `os.replace`; credit). But a last good copy is kept only for gear.json, and only before AI edits: rentals, kits, renters and profiles are overwritten with no previous copy, and the Back Up zip has no Restore. Keep the previous version of each file (or a few daily copies of the folder) and add Restore from Backup. There's no sign-in, so no caches to clear. |
| D-24 | S1 | bodega/core/store.py:535-543; ui/dialogs/profile.py:199-216 | The profile holds the prefix but no next number, so a series from an earlier system only continues if the first number is typed by hand, and typed numbers are never checked against other rentals. Add Next Number to Profile › Numbers (a saved value wins over the highest in use) and check every typed number. |
| D-32 | S1 | bodega/services/cobro.py:87-94; ui/window/transfer.py:72, 123-133 | Send to Cobro finds the Cobro profile by name and quietly uses the first one when the names differ, so renaming a profile in either app sends invoices under another letterhead. Re-importing finds existing gear by its name and department. Save the chosen Cobro profile's id (ask once) and keep each imported piece's source row. |
| D-37 | S1 | bodega/core/model.py:226-227; core/store.py:35, 373-385 | The app is named for itself and the sample rental house is made up (credit). But every new profile starts with 8.25% sales tax added to replacement values, and so to every automatic day rate, and with terms that say "the United States". Start sales tax blank and ask for it on the first profile, and make the country in the terms a field. |
| K-02 | S1 | bodega/services/cobro.py:154-169 | Most repeated actions are safe: Mark Booked, re-import, Get Photos (a second run is refused) and AI changes (only applied where unchanged). But sending to Cobro twice makes two draft invoices. Remember the sent invoice on the rental (D-16), and on a second send update that draft or ask first. |
| K-04 | S1 | ui/panels/rental.py:575-585; ui/window/editing.py:458-462; core/pricing.py:419 | Gear that's already promised can still be booked or marked Out: the shortage shows as a hint, but nothing stops it. Changes that touch several files (deleting gear, undo) aren't all-or-nothing. Decide whether a shortage blocks or asks (owner question), and make several-file changes recoverable if Bodega stops halfway. |
| K-06 | S1 | bodega/ui/window/main_window.py:736-749; ui/dialogs/checklist.py:132 | A failed save keeps the edits in memory and says so, but quitting then closes the window and loses them (verified with a full-disk save: the window closed and the edit was gone). Saves made outside `flush()` aren't retried, and Cancel or Esc in Check Out drops every tick and note without asking. On quit after a failed save, ask Try Again or Quit Anyway, and ask before dropping changed ticks. |
| K-12 | S1 | bodega/core/pricing.py:259-269, 325-363 | Rentals that are out or returned never lock their prices: lines without a typed rate are re-priced from today's gear, kit and profile rates, and gear names are read live. Verified: a returned rental's total went from $1,802 to $3,686 after one day rate changed, and to $5,278 after the profile's rate changed. Write each line's rate, name and days onto it when the rental is booked or goes out, and change it afterwards only through a recorded Reopen. |
| S-16 | S1 | ui/dialogs/update.py:47-50; core/update.py:417-450 | Almost all link checks use `web.web_link`, but `update.open_url` (release-note links, Get a Key) has its own `scheme == "https"` test, and the updater runs a generated bash/cmd script. Real risk today is nil (https only, system browser; paths quoted); fix by routing `open_url` through `web_link` and recording the helper script as a departure. |
| S-17 | S1 | ui/dialogs/profile.py:54-66; core/importer.py:288-300,361-370 | Photos are model behaviour (decoded by content, re-encoded, hashed names, 40/12 MB caps, Qt's 256 MB decode limit), but SVG logos are kept as they came with no size cap, and a probe showed Qt's SVG renderer pulls in a local image by plain path (`<image href="/path/x.png">`), so a hostile "logo.svg" could print a file from the computer into agreements. Spreadsheets have file and unpacked caps and never evaluate formulas, but no row/column/cell limits. Fix: render SVG logos to PNG on import (or strip non-data `<image>`), cap logo size, cap rows/cells. |
| S-21 | S1 | requirements.txt; .github/workflows/build.yml:98-99,212; .github/dependabot.yml | Credit: Actions pinned by commit hash, direct dependencies pinned exactly and few, Dependabot weekly, `persist-credentials: false`. Missing: transitive dependencies that ship inside the app (shiboken6, et-xmlfile, keyring's jaraco/SecretStorage/jeepney/cryptography…) float with no lockfile or `--require-hashes`; `pip install --upgrade pip` and `choco install innosetup` are unpinned; no vulnerability audit with fix windows (pip-audit), no SBOM, sdists not refused (`--only-binary`). Risk: a compromised or broken transitive release lands in a shipped build unnoticed. |
| S-23 | S1 | .github/workflows/build.yml:160-183; README.md:26-27; core/update.py:273-316,325-370,392-405; app.py:45-85 | Updates are good (https, SHA-256 from GitHub required, signed Macs must match the old Team ID), no deep links are registered, scanned label codes are validated, and the single-instance socket is same-user (0700) and only raises the window. But the shipped app isn't signed: Mac signing runs only if secrets exist (README says it isn't signed yet) and Windows has no Authenticode step, so people are taught to click Open Anyway / Run anyway and a tampered first download can't be told apart. Also: on Linux the socket lives at /tmp/bodega-&lt;user&gt;, which another local user can squat to make Bodega quit at launch. |
| X-01 | S1 | services/ai/providers.py:38,262-279; services/ai/tasks.py:238-287 | Cost drivers are the person's own AI bill and fetches to store sites. Per-call caps exist (answer bytes, page text, 600-piece prompt), but output tokens are capped only for Anthropic, a job makes one AI call and one fetch per piece with no count shown or ceiling, and there's no pause between requests to one store (risking the person's address being blocked). Fix: max_tokens on every call, show "this asks your AI N times" before a job, a per-job ceiling, a short pause per store. |
| X-06 | S1 | core/importer.py:361-370; ui/window/transfer.py:66-68; ui/dialogs/profile.py:54-62; core/web.py:204-212 | Most inputs are capped (web 6/12 MB and 15 s, AI answers 2 MB, chat 2,000 characters, feedback 5,000, sheets 50 MB / 200 MB unpacked, ids 64, links 2,048). Gaps: no row/column/cell caps on sheets, and a CSV cell over 131,072 characters raises `csv.Error`, which the import doesn't catch (probed: the import fails with no message); no logo size cap; no total deadline on a fetch, so Stop can't end a job stuck on a slow server. |
| X-08 | S1 | ui/dialogs/ai_setup.py:29-31 | No cloud of Bodega's own, so no budgets to set. But a job's worst case (pieces × calls) isn't known or shown, and AI setup never suggests setting a spending limit at the provider, the only spend cap a BYOK app can rely on. Shares the X-01 fix. |
| AI-01 | S1 | services/ai/tasks.py:1-15; SECURITY.md:15; ui/dialogs/ai_setup.py:30 | AI is off until the person connects a provider, and each job's purpose is written in tasks.py. But the app's own words give the wrong data scope ("gear names and links only") and nothing says what each feature must refuse. (The Project Addendum's AI block, added this round, now records the real scope.) A documentation fix. |
| AI-03 | S1 | services/ai/tasks.py:139-142,159-168,342-353,393-405,436-446 | Instructions are in the system part and the person's data in the user part, page text is wrapped in `<page>` with a "data, never instructions" line, and nothing the model reads can grant anything. But gear lists (often imported from shared spreadsheets or Google Sheets) go to Tidy Up Names, Organize Groups, Find Missing Links and the chat's `<inventory>` without that line. Risk is small (a planted name could only steer suggestions, which still go to Review); fix is one sentence per prompt. |
| AI-07 | S1 | services/ai/tasks.py:194-221,250-262; ui/panels/assistant.py:167-170 | Runs are fixed loops (no model-driven loops) with Stop, but nothing bounds a run's calls, time or cost, and Update from Links keeps calling the AI for every remaining piece after errors such as "out of credit" (each `AIError` is noted and the loop continues). Stop can't interrupt a fetch in progress. Fix: a per-job ceiling, stop after a few errors in a row, report the limit. |
| AI-08 | S1 | services/ai/tasks.py:466-481; ui/dialogs/ai_setup.py:30; README.md:129-130 | Renters and rentals are never sent (tested), and there's no retrieval or tenant to filter. But each question sends up to 600 pieces with what each cost, quantity, group, status and what goes with what, while Bodega says "gear names and links only", and nothing tells the person which providers may keep or train on what they send (e.g. some free tiers). Risk: the person's gear list and purchase prices reach a provider on terms they weren't told about; no renter data is at risk. |
| AI-09 | S1 | services/ai/providers.py:38,262-279; ui/panels/assistant.py:143-156 | Only Anthropic calls carry `max_tokens` (4,096); OpenAI-style calls (nine providers and Other) send none, and the 2 MB read cap doesn't stop billing (probed: body keys are only model and messages). One run at a time (good), but no usage tally, no limit per day or job, and no pointer to the provider's spend cap. The person's kill switch is Remove Key. |
| AI-13 | S1 | tests/test_ai.py; tests/test_ai_window.py | Good unit tests of the code guards with a fake provider (unsafe links ignored, allowed fields only, renters never sent, key never shown, redirects refused). Missing: an evaluation set of real naming/grouping tasks, a red-team set of injection attempts against the prompts, and a cost test of the worst-case job. Risk: a prompt or model change quietly makes suggestions worse (each is still reviewed). |
| R-03 | S1 | core/store.py:82-93,210-228; ui/components/photos.py:10; core/model.py:312 | No retention period exists for renters' details: every rental keeps its own copy of the renter forever (by design, a business record), set-aside copies of files are never removed, and photos are never deleted. Risk: renters' contact details are kept longer than needed with no way to age them out. Fix: a retention choice (e.g. forget renter contact details on rentals older than N years) or record it as a departure with the reason. |
| R-05 | S1 | core/store.py; core/fileutil.py:37-53; ui/window/transfer.py:156-170 | In transit is https everywhere (plain http only to a model on this computer) and keys are in the keychain. At rest, renters' details are plain JSON in the data folder and in Back Up zips, with no encryption or warning. Risk: a lost computer without FileVault/BitLocker, or a backup zip left in a shared folder, exposes renters' names, emails, phones, addresses and notes. Fix: say so at Back Up (or offer a password) and suggest disk encryption, or encrypt clients.json with a keychain key. |
| O-01 | S1 | .github/workflows/build.yml:18-238; GitHub branch settings | **Credit:** CI runs format, lint (bandit rules), the unit and window tests and the PyInstaller build on all four platforms, plus a packaged smoke test on each, and a red build blocks the release job. **Missing:** a type check (mypy/pyright) and a dependency vulnerability scan (pip-audit). Main is unprotected: 4 of 5 PRs (#7, #9, #10, #11) were merged before their CI run finished, and release commits went straight to main. The Windows installer step is `continue-on-error` (line 209), so a release can ship without the contract file `Bodega-windows-setup.exe`. **Fix:** add the two missing gates, require the build jobs on main, and drop `continue-on-error`. |
| O-04 | S1 | bodega/core/model.py:4, 42-44 | The hosted parts (zero-downtime deploys) are N/A. **Desktop translation, credited:** each PR uploads per-platform builds as previews, and old Releases stay downloadable for rollback. **Gap:** files have no format version, and `_known()` drops unknown keys, so an older Bodega opening newer files silently removes the newer fields the next time it saves. The model is unchanged since 1.0.0, so nothing has been lost yet. **Fix:** stamp a format version, and keep or refuse unknown fields. |
| O-05 | S1 | bodega/core/log.py:28-33; doc/export.py:62,103; ui/window/editing.py:409 | **Credit:** a rotating 1 MB × 3 log, never sent anywhere; no secrets logged (account.py:99, providers.py:190). **Gap:** the lines are free text, not structured. Full export paths are logged, which carry the OS user name and the renter's name (document.rental_stem), and so is the profile name. Request IDs are N/A (no server). **Fix:** key=value or JSON lines, and log names or counts instead of paths. |
| O-07 | S1 | ui/window/transfer.py:156-173; core/store.py:212-231; services/ai/tasks.py:488 | **Credit:** Back Up… writes one atomic zip of everything, and gear.json is snapshotted (20 kept) before AI changes. **Gaps:** no Restore command, and no test that restores a backup (test_back_up_zips_the_data only lists names). No automatic copy before an import, which can also overwrite the profile's rate and tax, or before Tidy Up Groups. Backups are unencrypted and on-device, and no RPO/RTO is written down. |
| V-04 | S2 | ui/style/theme.py, app.py | Reduce Transparency and Increase Contrast are never read; glass stays translucent and borders don't strengthen. Read the platform settings (macOS `NSWorkspace` accessibility flags, Windows high contrast) and swap to opaque, bordered tokens. |
| V-08 | S2 | tables.py group dividers; theme.py `DIVIDER_TEXT`; item panel "Where" chip | The accent colors things that can't be pressed: the gear table's group bands and their totals, the "+3" attached count, the Booked chip and the calendar's today. Keep the accent for what can be pressed or is chosen. |
| V-09 | S2 | panels/item.py "Rent This…", panels/rental.py "Agreement…", panels/kit.py footer | Footer actions of the inspectors are accent-filled; only + (and a sheet's confirm) may be. Make a record's next step the light raised capsule. |
| V-11 | S2 | tokens.py `GOOD`/`BAD`/`WARN` | Semantic colors don't follow the accent (pass), but each has only one value per look: no fill and soft value (danger has `BAD_TINT`, success and warning have none). Add text/fill/soft per meaning. |
| V-13 | S2 | tokens.py `FAINT`, accent_set() | Measured: `FAINT` text is 2.57:1 on the light page and 2.32:1 on the light glass (used for sidebar counts, hints, section labels); white on the accent in dark is 3.17:1 (Blue), 3.02:1 (Pink), 3.98:1 (Purple) for button words; Orange and Yellow as light text 4.22 and 4.40; `GOOD` 3.60 and `WARN` 3.84 as light text. `accent_set` picks white at 3:1, the standard needs 4.5:1 for words. |
| V-14 | S2 | tokens.py TEXT_* | One bundled family (Inter, Inter Display) plus one monospace (IBM Plex Mono) and no light weights: good. Sizes measured in use: 12, 13, 14, 18, 21, 24 px; 14 and 18 aren't Apple text styles and 24 isn't the Large Title (26). Replace TEXT_* with the pointer ramp of A.4 (26, 22, 17, 15, 13, 12, 11, 10) by style name. |
| V-16 | S2 | tokens.py fixed px sizes | Text sizes are fixed pixels; nothing follows the system's text size (macOS Accessibility › Text size, Windows text scaling) and nothing was tested at 200%. |
| V-17 | S2 | tokens.py CONTROL_H 34, TABLE_ROW_H 34, NAV_H 30, TOOLBAR_H 64, ICON 16 | Measured at 1280 × 900: buttons and fields 34 (28), circles 34 (28; bar circles 36), small icon buttons 24 (20), table rows 35 (44), sidebar rows 30 (32), switch rows 32 (44), icons in controls and the bar 16 (15 and 18); off-grid values in tokens (GRIP_GAP 5, CAL_BAR_INSET 7, MONTH_BAR_GAP 3, ROW_R 9) and in layouts (11 in MainWindow, 9 in the inspector stack). Spacing tokens themselves are on the grid. |
| V-23 | S2 | glass.py Dock, widgets.py Toast, lift.py | Timings are inside the defaults (dock 240, fades 150, toast 220/180), nothing waits on them, but Reduce Motion is never read: the dock slide, toast rise and row lift always animate. |
| V-24 | S2 | tokens.py + literals | Most values are tokens in one file (good). Literals remain: `padding: 2px` in theme.py (#KeyCap), `- 6` / `+ 2` offsets in tokens and code, `QColor("#…")` in tests/screenshot only. No z-order or shadow tokens per A.6 (GLASS_SHADOW_* exist). Audit with a script and move the rest in. |
| N-01 | S2 | ui/window/sidebar.py | Places, then the profile card at the foot (pass); no search capsule at the top of the sidebar (and no ⌘K palette). |
| N-02 | S2 | menus._app_menu | The card switches profiles, opens Settings, Send Feedback and Check for Updates (pass), but has no Keyboard Shortcuts item, and adds Edit Profile… and Add a Profile… that belong in Settings › Profiles. (Sign Out: no sign-in exists.) |
| N-03 | S2 | sidebar.py:132-143, menus.py:84-87 | The places are typed out twice: in the sidebar and in the View menu. Read both from one registry. |
| N-04 | S2 | main_window.py toolbar | Order is search, filter, share, assistant, +; the assistant's button belongs last, after +. No ⋯ More on list pages (fine where nothing else applies). |
| N-15 | S2 | menus.py:124 | A full menu bar on the Mac, but it's hidden on Windows and Linux (`setVisible(sys.platform == "darwin")`), and several commands live only in panels' ⋯ menus (Check Out…, Check In…, Send to Cobro…, Rent This…). |
| N-17 | S2 | — | No record pager (‹ 12 / 38 ›, ← →) in the inspector. |
| N-18 | S2 | dialogs/client.py, dialogs/profile.py | Gear, kits and rentals edit in place in the inspector (pass); a renter edits in a popup dialog; a new rental opens in the inspector rather than a sheet. |
| C-01 | S2 | widgets.Segmented, empty.StartTile | Word buttons are capsules and icon buttons circles (pass), but segmented segments are radius-6 rectangles in a radius-8 track and start tiles are cards that act as buttons. |
| C-03 | S2 | widgets.circle_button, icon_button | Every icon-only button has a tooltip, but none has an accessible name (no `setAccessibleName` anywhere), so a screen reader announces an unnamed button. |
| C-06 | S2 | main_window._row_menu (`m.addMenu(self._move_menu(...))`) | The gear row's context menu opens a Move To submenu on top of itself; a choice needing a list drills in. |
| C-08 | S2 | panels' menu_action("trash", …) | Menus open on click under their button and stay on screen (app.place_menu, pass); destructive items are last but not red. |
| C-11 | S2 | menus.py (`e = QMenu(self.btn_export)`) | The share button opens a menu of import and export formats first; it should open the page window on the list at once, with import in its own place. |
| C-12 | S2 | tables.py, panels/item.py Where chip | One table component (pass), figures right-aligned under their headings (pass), codes in the text color (pass); a rental's status shows as a tinted capsule in the gear panel, not a dot and a word. |
| C-13 | S2 | main_window | No count beside the title; a search that matches nothing leaves an empty table instead of "No Results" with Clear. |
| C-16 | S2 | filters.py | One filter circle, accent while on, Clear Filters (pass); active filters aren't shown as removable capsules under the title. |
| C-21 | S2 | widgets.date_field (QDateEdit) | Dates use Qt's own date box with a popup; the field cuts its own text off in the rental panel ("Sun, Oct 18, 202"). Build the compact date field of §G.22 (accent date, glyph, typing understood). |
| C-23 | S2 | — | Search in the bar (placeholder "Search", Esc clears) but no app-wide search: no sidebar search and no ⌘K palette; long inline lists (a kit's gear, a rental's lines) have no inline search. |
| C-24 | S2 | tables.py:282 filter() | Every word must match, case-insensitive (pass); accents aren't ignored ("cafe" doesn't find "Café"). |
| C-25 | S2 | tokens IMPORT_SIZE 760, REVIEW_W 900 | No nested dialogs (pass); the Import window (760) and AI Review (900) are wider than 640 and want to be pages or the print-sheet size. |
| C-26 | S2 | dialogs/* | Dialogs use the system's window frame and a Cancel button, not a ✕ circle; no scrim. (Esc closes and focus returns: pass.) |
| C-27 | S2 | dialogs/common.confirm | Alerts name the thing ("Delete Sony FX6?"), verbs, Cancel, Esc cancels, never at launch (pass); but deletes of gear, kits and rentals are confirmed even though Undo brings them back. |
| C-28 | S2 | editing.delete_* | As C-27: undoable deletes ask first instead of "Deleted. Undo". |
| C-32 | S2 | dialogs/settings.py | A window with its own sidebar; changes apply at once (pass); the sidebar has no search. |
| C-34 | S2 | 21 `status ==` comparisons in ui/ | Screens compare status strings (`r.status == "quote"` …) instead of asking the domain. |
| C-38 | S2 | lift.py | The table doesn't refill under a drag (pass); reordering gear has no keyboard or menu alternative (Move Up / Move Down). |
| C-39 | S2 | core/history.py, menus | Undo and Redo cover data changes (pass) but aren't named ("Undo Delete Item") and don't bring the restored thing into view. |
| C-44 | S2 | tables.py | Sortable headings (pass); no figure row, no tick on rows, no + to choose columns. |
| C-49 | S2 | panels/base.py | The inspector's header has ⋯ and ✕ only; no 🖨 ✎ capsule, and the next step is an accent-filled footer button. |
| C-53 | S2 | dialogs/preview.py | A live page preview with Print and Save PDF (pass); no columns to tick and reorder, no letterhead options, no presets. |
| C-58 | S2 | main_window totals | Totals ("Paid $21,223.46") count only pieces that have a value and don't say how many have none. |
| C-61 | S2 | dialogs/preview.py | The inventory page prints a group or everything; no Filter cards (Column, From, To). |
| C-65 | S2 | main_window._row_menu vs panels' menu_action | The row's context menu and the inspector's ⋯ are built separately and offer different things. One list of actions should feed both. |
| C-66 | S2 | panels/rental.py _number_typed | A rental's number can be typed, but a clash with another rental's number isn't said in the field. |
| C-67 | S2 | dialogs/profile.py "Delete This Profile?" | Most alert titles name the thing ("Delete Sony FX6?"); some don't ("Delete This Profile?"). |
| C-69 | S2 | tables.py RentalTable | The gear table gives up columns beside the inspector; the rentals table doesn't: its Dates column runs under the panel at 1280. |
| C-72 | S2 | `lib.settings.get(...)` throughout ui/ | Settings are read ad hoc by key in many places, with their defaults repeated; no one reader that reports an unusable value. |
| C-73 | S2 | tables.py | No ticks on rows (see C-44). |
| C-76 | S2 | — | A rental's next step (Check Out…, Check In…) can't be done for several ticked rentals. |
| C-82 | S2 | dialogs/client.py, profile.py | Addresses are one free-text box; no country or region. (Owner question: needed for a single-country rental house?) |
| C-100 | S2 | main_window._move_menu | The Move To list of groups grows with the data and has no search past 12. |
| C-108 | S2 | tables.py attached gear | Attached gear sits under its parent, indented 18 (pass), but the parent row doesn't open and close its children or sum them up. |
| C-111 | S2 | core/store.delete_item | Gear that rentals point to can be deleted (the rentals keep its name and price) rather than made inactive (Retired). Owner question. |
| C-117 | S2 | editing.delete_gear | The delete alert doesn't offer Retire for gear with history. |
| C-119 | S2 | dialogs/settings.py Account, services/account.py | Settings › Account shows a sign-in form for a service that isn't connected; nothing can sign in. Hide it until the service exists. |
| C-129 | S2 | panels/rental.py status dropdown | One family of words and tones (Quote, Booked, Out, Returned, Cancelled: pass), but the status is set by hand from a dropdown as well as by Check Out / Check In. Owner question. |
| C-160 | S2 | main_window.go, filters.py | Filters are never saved (pass) and survive opening a record (pass), but moving between gear places (All Gear → a group) keeps the filter and the search; search clears only when the kind of list changes. |
| C-163 | S2 | QComboBox | Menus stay on screen (pass); dropdown lists show 10 rows (Qt's default), not 8. |
| W-06 | S2 | ui/components/worker.py:38; ui/window/transfer.py:170,289; core/web.py:244; services/ai/providers.py:223; core/update.py:310; ui/panels/item.py:519,1013-1026 | Most messages say what happened and what to do. Four things break the rule. Background jobs can show "Something went wrong. Try again." Back Up and Save Calendar File show the raw `OSError` text (for example "[Errno 13] …"). Some messages carry codes ("said no (error 403)", "N of M bytes"). Check Price and link problems appear as toasts, not under the link field. Put each error beside its field, translate OS errors, and give unknown failures a short reference that matches the log. |
| W-09 | S2 | ui/dialogs/ai_setup.py:30; ui/dialogs/feedback.py:24; ui/dialogs/account.py:27; ui/dialogs/preview.py:182; ui/dialogs/profile.py:180,222; ui/panels/rental.py:263,401; ui/dialogs/import_sheet.py:91,95,102; ui/panels/rental.py:146 | Visible two-sentence descriptions explain dialogs. Many tooltips also run to two sentences, which the ladder forbids ("Dark Page: easier on the eyes while you work. PDFs and prints stay white."), and some tooltips only restate their label ("How many" on a quantity field). Cut each to nothing, or to one tooltip of a few words. |
| W-10 | S2 | ui/panels/assistant.py:70; ui/window/services.py:45,47; services/ai/tasks.py:463; ui/dialogs/update.py:208; ui/dialogs/account.py:27; ui/dialogs/ai_setup.py:30; ui/dialogs/profile.py:222; ui/panels/rental.py:54 | Exclamation marks and the app speaking as "I": "Hi! What can I help with?", "Thanks! Sent.", "Here's what I'd change.". There is filler ("Fixes and improvements.", "Accounts are coming soon.") and semicolons in hints and tooltips. Rewrite these as plain labels and sentences. |
| W-11 | S2 | ui/window/tables.py:936-939; ui/dialogs/gear_picker.py:58; ui/dialogs/import_sheet.py:120; ui/dialogs/settings.py:293; ui/components/widgets.py:126-129,154-156; ui/window/main_window.py:157 | Gear names cut short in the table get no tooltip, because only "with …" rows set one. Gear names in the picker and the import list are cut in the middle (that is for file names), while the data-folder path is cut at the end. `ElidedLabel` and the fold headers put the cut text into the widget itself, so screen readers get the shortened words. The selection count can be cut too. Keep the full text in the accessible name, add expansion tooltips, and use the right truncation mode for each kind of text. |
| W-12 | S2 | ui/window/services.py:61-64; ui/window/editing.py:336-338; ui/components/photos.py:59; ui/window/transfer.py:267; ui/components/worker.py:36-38 | Every failed update check reads "Couldn't reach GitHub. Check your internet", even when GitHub answered with something odd or a rate limit. Every save `OSError` reads "Check that there's free space on this computer", although permission, a read-only folder or a locked file are just as likely. Map each error kind to its real reason. The web and AI messages already do this well. |
| W-19 | S2 | core/earnings.py:1-6; ui/window/tables.py:508; ui/panels/item.py:945-960 | Earned (the table column and the panel line) is a share Bodega works out: a kit's or a camera line's price split by each piece's own day rate. It shows as an exact figure ("$1,234.56 on 3 rentals", "Paid Off 37%") with no "≈" and no tooltip saying how it was worked out. Mark it as an estimate and explain the split. |
| W-21 | S2 | ui/window/editing.py:322-338; ui/components/widgets.py:1000-1033; ui/dialogs/profile.py:159-196 | A failed save gives one message for every cause ("Couldn't save. Check that there's free space…") and no reference. Invalid input is neither stopped nor explained: "abc" typed in Paid Each, a day rate or a percent is quietly read as 0 or blank. Name the kind of failure (invalid field and what it takes, not allowed, disk full, unknown with a reference) and validate money and percent fields. |
| W-22 | S2 | ui/window/transfer.py:170,289; core/web.py:244; services/ai/providers.py:223 | Good: the Google Sheets and Cobro set-up messages name every step, and AI provider and web errors are translated in one place each. But operating-system errors reach people raw (Back Up, Save Calendar File), and two messages still carry status codes. Route OS errors through one translator as well. |
| I-01 | S2 | ui/style/theme.py:84; ui/components/panels.py:31-49; ui/panels/rental.py:72-80; ui/dialogs/settings.py:77-78; ui/window/sidebar.py:64-108; ui/panels/item.py:982; ui/window/calendar_view.py:178-181 | `* { outline: none; }` removes every focus ring. Buttons, switches, segmented controls and the accent picker show no focus at all. Tab never reaches these (verified offscreen): the sidebar places, Settings' sections, the profile card (switching profiles), rental line items (quantity, rate, own dates), Works With rows and calendar bars. Group rename, remove and move are right-click only, and custom gear order is drag only. Make the rows focusable with keys, give an alternative to each drag, and restore a visible ring. |
| I-02 | S2 | ui/window/menus.py:80 | Delete… is bound to Ctrl+Backspace as a window-wide shortcut, and it fires while typing. Verified offscreen: Ctrl+Backspace in the Company field opened "Delete Sony FX6…?" instead of deleting the last word, which is the standard text key on Windows and Linux (⌘⌫ on a Mac is likely the same; unverified). Return confirms that alert. Let text fields keep their editing keys (handle ShortcutOverride, or scope the shortcut to the tables). |
| I-03 | S2 | ui/window/main_window.py:100-101 | Esc is one window-wide shortcut that closes the panel. With text in the search field, Esc closed the inspector and left the search as it was, and a second Esc did nothing (verified). Make Esc clear the search first, then close one layer. Modal dialogs and menus do close one at a time. |
| I-06 | S2 | ui/dialogs/settings.py:103; ui/components/widgets.py:379-449 | New records and dialogs focus their first field (name, renter, search, scan box), and alerts focus the default button. Settings opens with focus on an invisible scroll area, not its first control (verified offscreen). The toast floats over the page's bottom rows, and nothing keeps a focused row in view under it. Return of focus to the opener couldn't be verified offscreen. |
| I-08 | S2 | ui/window/transfer.py:133-151; ui/window/menus.py:44,126-145 | Only gear exports to CSV, and it always writes every piece, ignoring the current group, search and filter. The Kits and Rentals lists have no export at all. Good: imports are previewed, can be undone with ⌘Z, and re-reading the same sheet reports "Nothing new in …". Export every list, using the rows it is showing. |
| I-11 | S2 | ui/window/menus.py:126-145,51-58; ui/window/common.py:24-28; ui/dialogs/preview.py:208-222 | The share button opens a menu of documents first (Inventory List…, Rate Card…, Labels…), and the File menu repeats each one. The page window does have a switch between the three documents, which is the right idea. Have the share button open the page window straight away, with that switch as a Document pop-up. |
| I-13 | S2 | ui/window/tables.py:218-230; ui/window/main_window.py:100 | Bodega has no single-key commands (N, E, D, /, ?, A). Verified: N and / do nothing on the gear list. What does exist behaves well: Delete and Backspace in a table ask first, and Enter never creates anything. Add the set behind a Settings switch, or record a ⌘-only departure. |
| I-14 | S2 | ui/window/main_window.py:165-174; ui/window/menus.py:82 | There is no type-select on the tables, though only by accident (column 0 is the empty grip column). ⌘F focuses the search, but / and ⌥⌘F don't. Inside the search, ↑ and ↓ don't move through the rows, and Enter only opens a scanned label code, not the marked row (verified). Add these keys. |
| I-15 | S2 | tests/test_window.py:902-908 | The only shortcut test checks that keys are listed. None of them is pressed in an end-to-end test, which is how the Ctrl+Backspace clash went unnoticed. Add a test that presses every listed key in its context. |
| I-19 | S2 | ui/window/editing.py:157-190; ui/panels/rental.py:617-623 | After deleting a gear row with the keyboard, no row is current (verified: the next row isn't selected). After New Renter… from a rental, focus doesn't move on to the dates or Add Gear. Select the neighbouring row, and move focus to the next step. |
| I-20 | S2 | ui/dialogs/profile.py:303; ui/dialogs/client.py:79-80; ui/dialogs/settings.py:212 | Save Changes and Save are enabled whenever a name is present, not only after something changed. Cancel and Esc leave at once even when typing would be lost. Each dialog decides this alone. Add one shared "changed" helper that compares the draft with what was loaded. |
| I-21 | S2 | ui/window/main_window.py:717-749 | Desktop translation of "the leave-page question": quitting while an AI job or Get Photos from Links is running stops it after a short wait and silently drops what it found, without asking. Edits themselves are saved on quit, so no question is needed for those. Ask before quitting only while a job is running. |
| I-23 | S2 | core/importer.py:363-366,517; ui/dialogs/import_sheet.py:47 | It reads UTF-8 with or without a byte-order mark, quoted thousands ("$1,299.00"), padded cells and header words. But the fallback is latin-1, not Windows-1252: verified, "Director’s Monitor 7”" imports as "Director\x92s Monitor 7\x94". Column choices aren't remembered for next time. Use cp1252 and save the mapping per sheet layout. |
| I-25 | S2 | core/importer.py:517; ui/dialogs/import_sheet.py:275-288 | "Total", "Equipment Total" and "Subtotal" rows are skipped but never compared. The preview counts items and pieces, but doesn't check the sheet's own total value or say whether it matches. Reconcile with the sheet's total row. |
| I-26 | S2 | core/importer.py:534,537 | A blank quantity is assumed to be 1 and a blank "Rent?" to mean yes, without asking. A blank Paid stays blank, which is right. Ask what a blank means for these columns in the preview. |
| I-29 | S2 | core/store.py:535-542 | No documents are imported, so the first two clauses don't apply. But the next rental number is the highest existing number plus one, so deleting the latest rental hands its number (whose PDF may already have reached a renter) to the next one. Keep a per-profile, per-year counter that never goes back. |
| I-30 | S2 | ui/window/menus.py; ui/window/tables.py:1078-1085 | In Qt-drawn popup menus (⋯, context menus, the filter menu), ↑ and ↓, → and ←, Return and Esc work and focus returns to the trigger. But Home and End don't jump, and typed letters don't jump to a matching row (verified offscreen). The Mac menu bar is native and does both. Add these keys to the shared menu. |
| I-31 | S2 | ui/window/tables.py:825-831; ui/components/panels.py:53-61; ui/components/widgets.py:188-238 | Gear-table dividers get Qt's → and ← for free, but folding by keyboard isn't remembered (only clicks update `folded`). Option-click to fold everything doesn't exist. The sidebar's foldable rows and their arrows can't be focused and announce no expanded state or child count, and neither do the Disclosure cards. |
| A-01 | S2 | tests/test_accent.py:15-22 | The only automated check is ON_ACCENT against the accent at 3:1. A quick token check fails: FAINT text, used for hints, alert bodies and placeholders, is 2.57:1 in light and 2.92 to 3.41:1 in dark. WARN "Out" in light is 3.84:1. Add accessibility tests for names, roles, focus and 4.5:1 text contrast on every main page, in both looks. |
| A-02 | S2 | ui/style/tokens.py:85 | Desktop translation: the minimum window is 1280×700 logical px, so with larger display scaling (for example a 1366×768 laptop at 125%, or a Mac's "Larger Text" at 1024×640) the window can't fit the screen and parts are lost. Lower WINDOW_MIN and let the layout give way. Text-spacing overrides don't apply, since a Qt app has no user stylesheet. Not checked on real hardware. |
| A-03 | S2 | ui/components/panels.py:53-55; ui/style/tokens.py:19 | The sidebar's fold arrows are 18×18 px, under the 20×20 minimum, and sit against their own row's click area. The section + is 20×20 next to the heading, which also reacts to clicks, so the 24-point spacing circle overlaps. Controls (34) and icon buttons (24) are fine. Enlarge or space them. |
| A-05 | S2 | ui/components/widgets.py:379-503 | Toasts are painted with no accessible text and no announcement (their accessible name is empty, verified). Status lines ("3 of 12 ticked", "Checking B&H…", errors under fields) aren't announced either. Announce them through QAccessible (QAccessibleAnnouncementEvent in Qt 6.8+, or a live label). |
| A-06 | S2 | ui/components/panels.py:31-136; ui/components/widgets.py:247-336,379; ui/window/calendar_view.py:50-181 | Sidebar and Settings rows show to screen readers as a nameless "Border" (verified). Every icon-only button has an empty accessible name (verified for the filter, share, assistant, +, ⋯ and ✕ buttons). The accent picker has no role or value, and calendar bars aren't exposed. On/off rows correctly read as checkable check boxes. |
| A-07 | S2 | ui/style/tokens.py:41-48; ui/components/glass.py:183,241-260; ui/components/widgets.py:402-421; ui/components/panels.py:92-96 | Every font size is fixed in px, so the system's text-size and Bold Text settings are ignored. Reduce Motion (the sliding inspector, rising toasts, fades), Reduce Transparency and Increase Contrast aren't read. Most statuses carry words, but the sidebar's Out Now count tells "late" from "out" by colour alone. Read these settings and add a non-colour mark. |
| A-11 | S2 | ui/window/editing.py:338; ui/components/widgets.py:410-475; ui/window/transfer.py:214,267 | Errors that need the person ("Couldn't save. Check that there's free space…", "Couldn't write the calendar file…", Check Price problems) are toasts that fade after a few seconds. Toasts have no actions, so the first clause doesn't apply. Keep such errors up until they are dismissed, or show them where the problem is. |
| A-12 | S2 | ui/components/widgets.py:84-106,126-129; ui/components/panels.py:70-76 | Fields aren't tied to their visible `Section` labels, so they read as a nameless "EditableText" (verified). Icon buttons have no name although their tooltips hold the words. Sidebar rows don't expose "All Gear" and the rest, and truncated labels expose the cut words. Set accessible names that start with the visible label. |
| A-13 | S2 | ui/components/widgets.py; ui/components/panels.py | The shared pieces (`Section`, `NavRow`, `Disclosure`, `ToggleRow` drawing, `AccentPicker`, `Toast`, `circle_button`) carry no names, expanded state, announcements or focus drawing. Esc handling isn't layered in them either: it's one window shortcut. Build these into each primitive once, so every screen gets them. |
| D-01 | S2 | bodega/core/document.py:14 | No Qt and no UI anywhere in core/ or services/ (credit). The one gap is document.py importing from the storage module (`store.terms_for`, `DEFAULT_TERMS`); move the terms text and `terms_for()` into a small domain module that store.py and document.py both use. |
| D-03 | S2 | ui/panels/rental.py:640; ui/window/sidebar.py:329 and tables.py:1052; filters.py:70-74; calendar_view.py:141 | pricing.py's own rules are in one place and well tested (credit), but screens also work out rules: a 10% deposit fallback, "Coming Up" written twice in the UI (using the rental's dates, not its lines'), which gear counts as booked or in, the same-day window on the calendar, plus 25 status-string comparisons in ui/. Move each into core with a test and have the screens ask. |
| D-05 | S2 | bodega/app.py:166-180; ui/panels/rental.py:640; services/cobro.py:134 | Errors are caught narrowly and logged (credit), but the central hook only logs: an unexpected error, or a disk-full error from a save outside `flush()`, gives the person no message and leaves the action half-done. Have the hook show a calm toast, and name the magic numbers (the 10% deposit, 15 payment days). |
| D-10 | S2 | bodega/ui/panels/rental.py:543-546 | No database, so this means "what must never be false is refused on write". Ids can't collide (they're dict keys and file names) and attachment loops are repaired on load (credit), but a typed rental number is never checked, so two rentals can carry the same number. Refuse, or warn about, a number already used. |
| D-16 | S2 | bodega/services/cobro.py:154-169 | Send to Cobro is a clean adapter (no Qt, plain errors, never touches Cobro's other files) and the .ics export keeps stable UIDs with a SEQUENCE that grows (credit). But the rental keeps no link to the invoice it became and has no "sent" state. Store the Cobro invoice id and number on the rental. **And it writes to the wrong place now:** Cobro became Saldo, which carries Cobro's folder over once and then reads only its own ("Saldo"); `cobro.data_dir()` still writes into "Cobro", so invoices sent after the switch land where Saldo never looks (verified in both codebases). Write to Saldo's folder (and say so by its new name). |
| D-22 | S2 | git history | Commit authors, message trailers and branch names should say only who owns the work and what it does. Some commits carried another author's name and lines after the summary, and some branches had generated names. Commits are the owner's, messages a plain summary; branches kind/description. |
| D-26 | S2 | core/model.py:365-367; core/earnings.py:18-19; core/pricing.py:422, 492; ui/window/calendar_view.py:188; sidebar.py:329; tables.py:1052 | Whether a rental still counts for something is decided in seven places (holds_gear, EARNED/COMING, two skips in pricing, the calendar, the sidebar, the table), so one rule can drift from another. Use one core function per question (holds gear, has earned, is coming up, shows on the calendar) everywhere. |
| D-34 | S2 | bodega/core/store.py:143-196 | Data saved by a newer Bodega (on a second computer, or in a restored or synced folder) opens with no notice and is saved back without the fields this version doesn't know. Once files carry a version (D-11), open a newer one read-only and say "Saved by a newer Bodega; update to edit". |
| D-42 | S2 | bodega/services/cobro.py:154-169; ui/window/transfer.py:294-325 | After Send to Cobro the rental doesn't say it was sent, and a failure is only an alert. Keep Not Sent, Sent (number and date) or Failed on the rental's link to Cobro and show it on the rental. |
| D-51 | S2 | bodega/ui/window/tables.py:232-246 vs 262-277; main_window.py:403-413; editing.py:192-198 | Select All and the selection use `showing_rows()` (no hidden rows, nothing inside folded groups), but `first_id()`, `_in_table()` and the selection count each walk the rows their own way and ignore folded groups. Use `showing_rows()` for every walk. |
| K-03 | S2 | bodega/ui/style/tokens.py:104-105; ui/window/editing.py:300-320 | Saving waits 400 ms after the last change and also happens before every command and on quit, and search filters on every keystroke (8–13 ms even at 3,000 pieces); credit. Missing: a maximum wait (steady typing never saves) and a save when the window loses focus or the app goes to the background. |
| K-07 | S2 | bodega/ui/window/transfer.py:54, 201-211; services/ai/tasks.py | Every outbound call has a timeout (15 s web, 90 s AI, 15 and 60 s updates, 30 s Sheets) and nothing retries, so nothing multiplies (credit). But the Google Sheets download runs on the window's own thread, freezing it for up to 30 s, and batch jobs keep trying every link when the network or the provider is down. Run that download in a Worker, and stop a batch after a few failures in a row and say why. |
| K-09 | S2 | bodega/ui/dialogs/checklist.py:132, 170-180; core/model.py:284-303 | Check Out and Check In ticks, notes and photos are kept on the rental, but only when Save or Mark is pressed (Cancel drops them), and no row records a time. Save each tick as it's made and stamp each row's time, and later who did it. |
| K-10 | S2 | bodega/ui/window/transfer.py:72, 84-104; core/importer.py:553-560 | Importing a sheet again adds only what's missing and fills blank links without overwriting curated gear, and attached gear goes in with its parent in one pass (credit). But rows are matched by name and department, so a renamed piece comes back as a duplicate. Keep each imported piece's source key (sheet and row) and match on that. |
| P-01 | S2 | bodega/core/pricing.py:55-58; core/earnings.py:41; ui/window/tables.py:842; ui/panels/item.py:947 | Quick with the sample (window open 0.46 s, refresh 73 ms), but the work grows faster than the data. At 1,000 pieces and 500 rentals, the table refresh after each edit takes 0.56 s and opening a piece 0.51 s; at 3,000 and 2,000 the window takes 9.3 s to open and a piece 4.5 s. `children()` scans every piece for every node and earnings re-prices every rental on each refresh and each open; index children once per call and compute earnings once per change. |
| P-02 | S2 | bodega/core/history.py:16-35; ui/panels/item.py:534; ui/window/ai.py:106; ui/window/services.py:58 | Thumbnail, icon and font caches have size limits (credit). But undo keeps up to 100 full copies of everything (about 2.4 MB each at 1,000 pieces and 500 rentals, about 9 MB at 3,000 and 2,000), and every finished price check, AI job and update check stays alive under the window. Keep only the changes (or cap undo by size), and delete each thread when it finishes. |
| P-09 | S2 | bodega/ui/window/transfer.py:54, 168 | AI jobs, photos, price checks and updates run in the background one at a time (credit). The Google Sheets download (up to 30 s) and Back Up (which zips every photo) run on the window's thread with no progress and no Stop; move both into a Worker. |
| P-13 | S2 | tests/ | The packaged app is smoke-tested on every platform, but no test runs Bodega with a large collection, which is how the slowdowns in P-01 went unnoticed. Add a scale test (for example 3,000 pieces and 2,000 rentals) that records how long it takes to open, refresh, open a piece and edit a rental. |
| P-15 | S2 | core/store.py:413-445; core/history.py:66-79; core/pricing.py:419 | Bulk work (deleting many pieces, Tidy Up Groups, applying AI changes, undo, import) has never been timed on a large collection. Measured here at 3,000 pieces and 2,000 rentals, checking one rental's shortages takes 0.47 s and each undo snapshot 80 ms, and both run after every edit. Time them in the scale test (P-13) and set a limit. |
| S-25 | S2 | SECURITY.md; CONTRIBUTING.md:66-67; core/update.py:18-19 | Private vulnerability reporting and a protections table exist, and Ruff's bandit rules run in CI. Missing: written accepted leaks (stores see the person's address and product links; AI-suggested links are fetched; the Linux socket name), an incident plan (pulling a bad release, a leaked signing secret), and the docs have drifted: CONTRIBUTING rule 9 says the only network use is GitHub, the update docstring says once a day (it checks every launch, ui/window/services.py:54), and "only gear names and links" go to an AI (not true, see AI-08). |
| AI-11 | S2 | ui/panels/assistant.py:197-203; ui/dialogs/ai_review.py:39-46 | Answers are labelled "AI" and Review shows where page-based changes came from, but chat answers don't say which pieces they came from, and nothing flags an uncertain suggestion (e.g. a name the model guessed); the From column is empty for Tidy and Organize. |
| AI-19 | S2 | ui/window/ai.py:36,119-135 | A change asked for in the chat opens the separate Review window rather than a card in the conversation with Decline and "Change N Items"; the field isn't disabled while it waits, and the outcome is a toast. (Review for the jobs is right.) |
| AI-23 | S2 | services/ai/tasks.py:41,435-462 | A bulk request in the chat ("put the Aputure lights in a group") is listed piece by piece by the model, and only the first 600 pieces can be reached, so in a bigger inventory the rest are silently left out. Fix: let the model name a rule and filters (group = X where company = Aputure) and have Bodega work out every piece. |
| AI-28 | S2 | services/ai/tasks.py:38 | There are no rule tools, and chat changes reach gear only, not kits. Keeping renters away from the AI is a sound exception (see departures). |
| AI-29 | S2 | services/ai/providers.py:213-221; ui/dialogs/ai_setup.py:66-78 | Each question stands alone (no stored conversation) and no optional features are used, so the first two parts don't arise. But a chosen model the provider has dropped isn't flagged in Settings; it only fails at use with "That model or address wasn't found". |
| AI-30 | S2 | tests/test_ai.py:49-61; tests/test_ai_window.py:44-122 | The provider is faked at the transport for setup, keychain, a plain-text answer and Accept (Tidy end to end). Not covered: Cancel in Review, a chat change through Review, and trying each real provider once with a fake key to see its refusal in plain words. |
| AI-31 | S2 | ui/dialogs/ai_setup.py:29-31; ui/panels/assistant.py:70-74 | The only words are "Use your own key. It's kept in your keychain; only gear names and links are sent", which understates what's sent and says nothing of what protects them (it only proposes, renters never go, links are checked) or what stays true (it can be wrong, data goes to the provider they chose). |
| R-01 | S2 | core/model.py:186-195; SECURITY.md; README.md:129-130 | Collection is minimal (renters: name, company, email, phone, address, notes; no ID or card numbers; all optional). But there's no data inventory saying what personal data sits where (JSON files, Back Up zips, set-aside copies, logs), how long, and what each outside service receives (AI provider: gear and prices; GitHub, stores, Google: requests from the person's address), and the current statements are partly wrong (see S-25, AI-08). |
| O-09 | S2 | build.yml:29,87; pyproject.toml:11,36; CLAUDE.md:4 | **Desktop translation:** the bundled Python is the production runtime. CI uses a floating `"3.12"`, pyproject allows `>=3.11` (ruff targets py311), CLAUDE.md says 3.12, and this dev environment runs 3.13.16. **Fix:** add a `.python-version` with an exact 3.12.x, use `python-version-file` in setup-python, and align `requires-python` and the ruff target. |
| O-11 | S2 | bodega.spec:6; ui/dialogs/settings.py:168 | The uncached endpoint is N/A. **Desktop translation of "every build carries a stamp" (§16.2):** builds carry only the hand-typed `__version__`, so a PR artifact built from this branch says "1.2.2", just like the coming release, and the updater would never offer the real 1.2.2 to it. **Fix:** stamp the commit (GITHUB_SHA) into the bundle and show it under the version in Settings and About. |
| T-01 | S2 | tests/conftest.py:31-38; core/sample.py; tests/*.py | **Credit:** an autouse fixture gives every test an empty temporary data folder. screenshot.py uses a throwaway folder, and the sample uses `.example` addresses and 555 numbers. **Gap:** about 24 of 190 tests are named for a feature, not a behaviour (`test_xlsx`, `test_groups`, `test_toasts`, `test_export_pdf`, `test_meta_tags`, `test_update_window`…). |
| T-03 | S2 | tests/test_pricing.py; core/pricing.py:366-370, 465-481, 509-521 | **Credit:** core rules are mostly covered (pricing 88%, store 88%, money 91% by line). **Untested:** `suggested_deposit`, `schedule()` (the calendar), `units_out`, `units_needed` and rounding half-boundaries in `money.whole`/`cents`. Also untested: zero, negative and blank quantities or values in pricing, numbering across a year change, and leap days. Tests read the real clock (`date.today()`, `sample.fill`) instead of fixing it. |
| T-04 | S2 | tests/test_window.py | **Credit:** the main journeys drive the real MainWindow offscreen (add, edit, attach, import, kits, rental statuses, check out and in, export, delete, undo, settings) and often re-read the Library from disk. **Gaps:** controls are reached through private attributes (`t._lift`, `d.accent._pick`, `rentals._open_editor`), not stable IDs, and only at the default window size, never at WINDOW_MIN (1280 × 700) or wide. Phone and tablet sizes are N/A: desktop only. |
| T-06 | S2 | tests/ | No memory test (open and close screens, then compare to baseline), and no load run with production-sized data (years of rentals, thousands of pieces). Failure drills exist only in part: AI provider errors and refusing stores (test_ai.py, test_photos.py). |
| T-09 | S2 | tests/conftest.py:19-28; build.yml:110-115 | A known crash, Qt objects crashing at interpreter shutdown after the tests pass (Windows), has been masked twice since 1.0.0: `os._exit` in conftest, and log-parsing in CI. It has been neither fixed nor pinned. Today the run is clean here; the packaged app's own exit code is still checked by the smoke tests. |
| T-11 | S2 | tests/ | No layout measurement at all. Nothing checks circles are square, rows and choice rows are at their tokens (e.g. TABLE_ROW_H, LIST_*), fonts are above the minimum, the edges match, or pop-up widths. The only geometry asserts are inspector widths and the toast's placement. Touch and phone modes are N/A (desktop). |
| T-12 | S2 | tests/test_window.py:387-398, 483-488; tests/test_documents.py:51 | **Credit:** effects are proven by reloading the Library from disk. **Gaps:** PDFs are checked only by size and `%PDF`, never read by an independent reader. Qt warnings ("does not support grabbing the keyboard") don't fail the run. test_toasts waits a fixed 500 ms by wall clock; `wait_for(done)` exists and should be used. |
| T-14 | S2 | ui/window/tables.py:173-176; ui/panels/base.py:88-90 | Rows have a right-click menu (`menu_wanted`) and records have ⋯ (`more_menu`), but no test compares the two sets. |
| T-15 | S2 | tests/test_update.py; build.yml:133-162 | **Credit:** the update flow is unit-tested with fakes (local server, monkeypatched release, helper scripts run for AppImage and folder). **Gap:** it never runs in a packaged build. The smoke tests don't exercise it, and `_auto_check_updates` skips source runs, so a frozen build is never tested against a faked newer release. |
| T-16 | S2 | CLAUDE.md:"Before finishing"; PRs #7-#11 | **Credit:** the rule to run ruff and the full pytest before finishing is written, and CI runs everything per PR. **Gap:** real results appear in only 1 of 5 PR bodies (#8), and 4 PRs were merged before CI finished. The screenshot suite is not part of "every suite". |
| T-18 | S2 | tests/ | There is no automated G.28 measurement suite, not even in pointer mode with light and dark. Touch (1280 × 900) and phone (390 × 844) are N/A for a desktop-only app, but the pointer checks (1-5, 7-13, 16-17, 19) apply. |
| G-01 | S2 | repo root; CONTRIBUTING.md:17-18, 66, 96; THIRD_PARTY_NOTICES.md | **Present:** README, CLAUDE.md, CONTRIBUTING and DESIGN (instructions), CHANGELOG, SECURITY, THIRD_PARTY_NOTICES, LICENSE. **Added this round (2ad6fa3):** CLAUDE.md points at the standard and docs/PROJECT_ADDENDUM.md. **Missing:** an overview naming the commit it measured, and a scope map. **Not current:** CONTRIBUTING names `test_money.py`, `test_render.py`, `make_fonts.py` and `ui/update_dialog.py` (none exist), and says the only network use is GitHub. Notices omit et_xmlfile, jaraco.*, more-itertools, SecretStorage, jeepney, cryptography/cffi, pywin32-ctypes and the PyInstaller bootloader. README's screenshot shows the old violet look. |
| G-02 | S2 | CLAUDE.md:177-179 | No list of open decisions (with who and when). "Ideas not done yet" has two deferred features, not questions, and nothing records answers. Examples to record: tax on deposits, currency, what week billing defaults to, rollback support. |
| V-15 | S3 | theme.font(), tables.py | No tabular figures anywhere (no `tnum` feature set), although Inter has them; totals and money columns don't line up digit for digit. |
| V-18 | S3 | tokens.py RADIUS_* | Capsules and circles are right. The scale is 4 · 6 · 8 · 12 · 18 (and ROW_R 9) instead of 4 · 8 · 10 · 14 · 18 · 20: fields 8 (10), cards 12 (14), glass 18 (20), chips and segments 6, table highlight 9 (6 by the concentric rule). |
| V-19 | S3 | ui/components/empty.py StartBadge; sidebar Avatar | One line icon set drawn from `theme._SVG` (pass), but start tiles put icons on tinted filled discs and the profile monogram is an accent-tinted disc. |
| V-22 | S3 | sidebar.py wordmark; titlebar.py | On a Mac the "bodega." wordmark is drawn twice at once (the title bar and the top of the sidebar). Keep one (the title bar, or none: the window's name is enough). |
| V-25 | S3 | widgets.Segmented | The segmented control switches its highlight in place; it doesn't slide. |
| V-26 | S3 | tokens.py LIGHT | The light neutrals are fixed greys/whites; they don't take a tint from the accent in a perceptual space. |
| V-28 | S3 | tokens.ACCENTS, Settings › General | The accent is per person and devices (settings.json); documents print in the profile's Paper Color (pass). The first choice isn't the profile's color ("Company Color"); it's Bodega's blue. |
| V-32 | S3 | theme.py `:disabled` rules | Disabled is drawn per control (FAINT text, `ACCENT_OFF` fills, transparent scroll bars) rather than one 40% opacity. |
| V-33 | S3 | theme.py `#PageTitle` 24 Bold, `#BigName` 18 Bold | The page title is 24 (Large Title is 26) and a record's name 18 (Title 1 is 22). |
| V-35 | S3 | tokens.TRACK_TITLE −0.4, TRACK_BRAND | Letter spacing is set by hand: titles are squeezed to −0.4 px at 24 px, tighter than Apple's (about +0.1 at that size). Inter has no optical sizes, so follow Apple's tracking table. |
| V-36 | S3 | main_window toolbar vs table | The page title starts at x 268 and the table at x 252: two left edges. On a computer the margin is the large title's inset (28). |
| V-37 | S3 | main_window layout | At 2200 wide the table runs from 252 to 2189: no maximum width, not centred. |
| V-40 | S3 | RADIUS_LG 12 | Cards and start tiles (card-sized) use 12; 14 or more. |
| V-41 | S3 | scripts/make_icon.py | The icon is drawn by a script (good) but from code, not one vector source, and framing isn't measured from the mark's bounds. |
| V-42 | S3 | theme.py | No style carries its own line height; Qt's default line height is used for every size. |
| N-05 | S3 | main_window.py toolbar | Filter, share and assistant are separate circles; icon buttons that sit together share one capsule. |
| N-06 | S3 | main_window.py `self.title` | The title sits in the bar's row (the native-toolbar choice §3.3 allows, used on every page: pass) but no count beside it. |
| C-04 | S3 | main_window toolbar | Share/export shows on an empty gear page; disabled buttons rarely say why in a tooltip. |
| C-17 | S3 | panels/item.py | The name is 18 (Title 1 is 22), the photo sits above the name rather than beside it, and there's no number · status line or figures strip in the head. |
| C-19 | S3 | panels/rental.py renter, panels/item.py group | Switches in rows and segmented controls are right; the renter and group pickers can pass 12 choices with no search. |
| C-29 | S3 | widgets.Toast.show_message | Centred above the totals, a few words, success 3.5 s (pass); a problem toast also leaves after 3.5 s (warning 6 s, an error that needs the person stays until dismissed). |
| C-37 | S3 | tables.py | Shift and ⌘ click select (pass); no selection bar for what can be done to several. |
| C-42 | S3 | tooltips throughout | Many tooltips are full sentences with full stops ("Pick up Friday, return Monday: billed as one day. New rentals start with this.") and run past 75 characters. |
| C-45 | S3 | tables.py | Columns can't be dragged into another order or chosen. |
| C-47 | S3 | empty.py | Empty lists show start tiles (consistent across places); no "No Results" view when search or filters hide everything. |
| C-50 | S3 | `#BigName` 18 | A record's name is 18 Bold, not Title 1 (22). |
| C-54 | S3 | lift.py | Grips, a lifted row and live sliding (pass); no ↑/↓ move from the keyboard. |
| C-55 | S3 | tables.py | The table isn't in a card, so its pinned headings have no rounded corners to keep. |
| C-59 | S3 | main_window, panels | Two left edges (title 268, table 252); cards inside cards in the inspectors (a rental's line boxes inside the Gear card). |
| C-70 | S3 | dialogs/settings.py | No account card at the top of Settings; Import lives in the bar's share menu, not in Your Data. |
| C-88 | S3 | core/tidy.py | Gear names and groups change by rule (Tidy Up); renters' names and addresses can't. |
| C-90 | S3 | panels/*, profile.py | Pop-ups and text fields stretch to the column's width instead of hugging their value / sized by kind. |
| C-105 | S3 | tables.py RentalTable | Headings are Title Case nouns, but "Dates" is cut off beside the inspector. |
| C-106 | S3 | tables.py gear names | Attached gear shows "with Sony FX6 Cin…" as grey text inside the name cell; make it a column or leave it to the record. |
| C-114 | S3 | dialogs/profile.py, client.py | Return in a dialog's field presses Save instead of moving to the next field. |
| C-120 | S3 | dialogs/settings.py | Profiles is a long form, not grouped rows; General's rows aren't in grouped cards. |
| C-138 | S3 | main_window | Print/export is offered on an empty gear page. |
| C-164 | S3 | renter, group, Move To lists | Lists past 12 choices have no search. |
| C-167 | S3 | tokens TOGGLE_ROW_H 32 | A switch row is 32, not 44. |
| C-168 | S3 | tokens TOGGLE_W/H 36×20, theme | The switch is 36 × 20 and the accent when on; 44 × 26, green. |
| W-02 | S3 | ui/panels/kit.py:35,176; ui/panels/rental.py:268; ui/dialogs/common.py:177; ui/window/tables.py:917,1004; ui/window/sidebar.py:316; ui/window/transfer.py:120; ui/dialogs/import_sheet.py:125,287; ui/dialogs/ai_review.py:68; ui/dialogs/gear_picker.py:166; ui/window/editing.py:198; ui/window/menus.py:92 vs ui/dialogs/settings.py:38 | Several things have two names. Kit is also called "package". A gear record is "piece", "item" or "gear" ("Make It Its Own Item", "Added 3 items.", "Delete 3 pieces of gear?"), and "piece" also means a unit. Other pairs: "Untitled Kit" / "New kit", "Tick All" / "Select All", "picked" / "selected", "Match the System" / "Match System", "Add a Profile…" / "Add Profile", "/day" / "a day". Pick one word for each, put it in a vocabulary list and carry it through. |
| W-03 | S3 | ui/dialogs/feedback.py:24; ui/dialogs/ai_setup.py:30; ui/dialogs/account.py:23-27; ui/panels/assistant.py:70-73; ui/dialogs/common.py:145; ui/dialogs/feedback.py:38; ui/dialogs/import_sheet.py:90,101 | Dialogs open with subtitle sentences under their titles: Feedback ("An idea, something that went wrong, anything. It's read by a person."), AI setup, Sign In, the assistant's greeting and Tidy Up's preview. Several labels run past four words ("Include Bodega's version and the kind of computer", "Attach Gear Made for Other Gear"). Delete the subtitles and shorten the labels. |
| W-04 | S3 | ui/window/main_window.py:526,529,365; ui/dialogs/account.py:23; ui/dialogs/settings.py:292; ui/window/filters.py:33; ui/panels/item.py:211; ui/window/transfer.py:170,289; ui/dialogs/feedback.py:38 | Some titles and controls are in sentence case: "Add your profile", "Nothing selected", "Sign in to your account", the "No group" placeholder, the "Couldn't back up" alert title and the checkbox "Include Bodega's version…". Others capitalize small words ("Saved On This Computer", "Not For Rent"). Tooltips mix the two styles ("New Kit" next to "New gear or group"). Apply §5.3 everywhere. There is no ALL CAPS in the app itself. |
| W-05 | S3 | ui/window/transfer.py:91,120; ui/window/groups.py:145; ui/dialogs/common.py:145; ui/dialogs/import_sheet.py:284; ui/dialogs/gear_picker.py:81; core/document.py:320; ui/components/widgets.py:849-850 | Some plurals break at 1: "Added 1 items.", "Its 1 pieces stay", "1 pieces get a clearer group", "1 of 1 items", and "1 items" on the printed inventory. Dates are forced to US English and money to "$1,234.00", whatever the computer's locale. Give every count a real singular, and either read locale formats or record US-only as a departure. |
| W-08 | S3 | whole UI (no translation layer); ui/window/editing.py:177-183; ui/components/widgets.py:849-850 | Strings are hard-coded English with no translation layer. Sentences are built from fragments ("The {n} piece{'s'} attached go{'es'} too. " + "Rentals that had them…"), and plurals are made by adding "s". Formats are fixed to en-US and nothing mirrors for right-to-left. Route strings through Qt's `tr()` with whole-sentence placeholders, or record "English only" as a departure. |
| W-14 | S3 | ui/panels/rental.py:300-345; ui/panels/kit.py:240-243 | The rental panel's header says "Rental" and its first card is also titled "Rental". Check Out… sits in the footer and again in the ⋯ menu. A folded kit "About" card repeats the kit's name, which shows as the big title just above it. Rename the card, and keep each next step in one place. |
| W-15 | S3 | ui/window/menus.py:92,99,102,173; ui/dialogs/settings.py:198; ui/dialogs/shortcuts.py:16; ui/window/editing.py:249,264; ui/panels/item.py:352; ui/panels/assistant.py:57 | Labels carry articles: "Add a Profile…", "Match the System", "Close the Panel", "Add to the Rental", "Choose a File…", "Connect an AI". AI › Assistant (⌘J) shows and hides the assistant, but its wording never changes. Drop the articles, and make it Show Assistant / Hide Assistant. |
| W-16 | S3 | ui/window/editing.py:177-178,360; ui/window/groups.py:46,150; ui/window/editing.py:231 | Toasts and alert bodies add "." straight after data: `f"Saved {c.name or c.company}."` turns "Northwind Media Inc." into "Inc..", and the same happens with group and gear names in the delete-alert list. Fragment alert titles correctly have no full stop. Check for a closing full stop before adding one. |
| W-17 | S3 | ui/panels/item.py:166; ui/window/groups.py:87; ui/panels/item.py:270; ui/panels/kit.py:76; ui/panels/rental.py:414; ui/dialogs/preview.py:135 vs 153; ui/panels/item.py:163 vs ui/window/menus.py:104 | "Rent This…" creates the quote straight away, so it needs no "…". "Remove Group" asks first but has none. "Add Gear" opens the gear picker in three places without "…". The same command is written two ways in two places ("Email Renter" / "Email Renter…", "Update with AI" / "Update from Links…"). Words for work under way use the single "…" character correctly. |
| W-18 | S3 | ui/window/filters.py:25,192; ui/window/groups.py:24; ui/panels/item.py:211,792 | The filter's choice that keeps everything reads "Any Company" and "Everything", not "All Companies" or "All Gear". Group pickers say "No Group" (and the placeholder "No group"), not None. There are no dashes or italic prompts, and "Choose a Renter" follows the pattern. Rename these choices. |
| W-20 | S3 | ui/window/transfer.py:271,291; ui/panels/item.py:66,239; ui/dialogs/import_sheet.py:281 | Directions are written out as paths: "For Google Calendar: File › Save Calendar File…" (on Windows and Linux there is no File menu), "In Google Calendar: Settings › Import & Export › Import.", "(your profile's Pricing)", "Check which column is the Name under Columns". Give each one a button or link that opens the place. |
| I-04 | S3 | ui/dialogs/shortcuts.py:13-17; ui/window/main_window.py:194; ui/window/menus.py:47-48,108,122-124 | Good: the shortcut list reads the menu actions. But tooltips are typed by hand ("AI Assistant (⌘J)" shows ⌘ on Windows and Linux), the "Anywhere" keys are a separate list, and there is no command palette. On Windows and Linux the menu bar is hidden, so Save Calendar File…, Quick Tidy Up Groups…, Open Log File, About Bodega and Add Rentals to Calendar can't be reached at all. Drive tooltips and every surface from the action registry. |
| I-09 | S3 | ui/style/theme.py:213-217; ui/components/widgets.py:616-631 | Scroll bars are restyled with QSS, which turns the Mac's overlay bars into permanent drawn ones. `FitScroll` keeps a scroll gutter always on. Leave the system's scroll bars alone on macOS, and elsewhere show a thin thumb only while scrolling. |
| I-10 | S3 | ui/dialogs/preview.py:116-125 | The page window uses a plain `QScrollArea` with a restyled bar, shown only when needed. Nothing says which page is in view while scrolling ("Page 2 of 5"). Give the preview its own always-visible bar with a page readout. |
| I-12 | S3 | ui/window/menus.py:84-87 | ⌘1–⌘4 go to All Gear, Kits, Rentals and Calendar, but the sidebar is grouped. The numbers skip the group rows, the kit rows, Out Now and Coming Up, so they don't run down the sidebar in order. Drop them, or number every row in sidebar order. |
| I-18 | S3 | ui/style/theme.py:112,147,267,309; ui/window/main_window.py:181-204 | Table rows get a tint, which is correct. But filled controls (circle buttons, capsule buttons) and start tiles that open something only change their tint on hover, with no lift. Toolbar buttons sit 8 px apart, leaving dead gaps between their hit regions. Add a lift where there is room, and make neighbouring hit regions touch. |
| A-10 | S3 | ui/style/theme.py:84,172,242,326; ui/window/tables.py:328-383 | A focused table row correctly shows as the row's highlight. But buttons, switches, segments and menus-on-buttons have no focus ring at all, fields only change their 1 px border colour (thinner than the 2-point ring), and the accent picker's ring is 1 px. Add a 2-point ring at 3:1 to every control. |
| D-04 | S3 | bodega/ui/window/menus.py:35-60, 125-150 | Places (`common.TITLES`) and pages (`PAGE_DOCS`) are registries (credit), but commands are declared again by hand in each menu (menu bar, Import & Export, the + menus, ⋯ and right-click), with different names for one command ("Print Inventory List…" / "Inventory List…"). Keep one command table (name, key, icon, function) that every menu builds from. |
| D-20 | S3 | bodega/core/model.py:157, 186, 212; core/fileutil.py; ui/window/common.py | One thing goes by two names: the screen says Kit, Renter and Profile while the code and files say Package, Client and Business. Module names are vague (fileutil, common) and one-letter names (b, r, it, ln, d, p) appear far outside loops. Rename across the code in one change, keeping the old file names readable. |
| D-21 | S3 | e.g. core/model.py:51, core/pricing.py:34; tests/test_importer.py:75, tests/test_store.py:12 | Comments mostly explain why, in plain sentences (credit). But there are 116 `# ------ name` banner comments, and some tests are named by topic (test_xlsx, test_google_sheets, test_round_trip, test_groups, test_meta_tags); CONTRIBUTING §4 is also out of date about threads. Remove the banners and rename those tests as sentences. |
| D-23 | S3 | pyproject.toml:35 | Formatting is automatic and enforced in CI (credit), but the line length is 110, not the shared 120. The folder layout couldn't be compared with the owner's other apps (Unverified). Use 120, or record 110 in the Addendum. |
| D-25 | S3 | bodega/ui/window/pages.py:44, 61-93 | The page window takes its list of documents from `PAGE_DOCS` and draws every page from one DocView (credit). But which builder, file name and tools a page gets is an if-chain on the document ("ratecard", "labels", "kit", and Copy/Email/Mark Booked only for rentals). Put the builder, file name and tools into each `PAGE_DOCS` entry. |
| D-31 | S3 | ui/dialogs/*.py (19 × `setObjectName("Primary")`); ui/window/tables.py:1015; ui/panels/rental.py:42; core/document.py:16 | The confirm button is hand-built in 19 places by setting an object name rather than coming from one button component with a variant, and the status words exist in three copies. Add `button(kind=…)` and one status-words table in core, then search to prove no copies are left. |
| D-41 | S3 | bodega/core/model.py:306-333 | An account service is already designed to plug in (services/account.py), but rentals have no "by" fields for booking, check-out or check-in. Add empty booked_by, checked_out_by and checked_in_by now, filled only from a signed-in account and never typed. |
| D-49 | S3 | bodega/ui/panels/rental.py:638-640; services/cobro.py:134; core/store.py:383-384 | In places zero is treated as "not set": a profile deposit of 0% still suggests 10%, Cobro payment terms of 0 days become 15, and a sheet rate of 0 falls back to the default. Test for blank or None instead of truthiness. Late results do check that the piece is still open (item.py:694). |
| P-03 | S3 | .github/workflows/build.yml; core/store.py:175-186 | Start-up reads every rental file ever saved (182 ms at 2,000, fine for now), and CI has no size limit for the packaged app. Add an app-size check to CI. |
| P-04 | S3 | bodega/ui/window/services.py:56-67 | The screen never goes blank while it refreshes, and a second price check, photo run or AI job is refused while one is running (credit). But pressing Check for Updates while the automatic check is running starts a second request; reuse the one in flight. |
| P-16 | S3 | ui/window/tables.py:842; ui/panels/item.py:947 | Counts are cheap, but the expensive total (what every piece has earned, which re-prices every rental) is worked out again on every gear refresh and every time a piece opens, even when the Earned column is hidden. Work it out once after rentals or prices change and reuse it. |
| AI-14 | S3 | ui/window/main_window.py:189-203; ui/style/theme.py:396; ui/window/menus.py:102 | The button is a speech bubble, not a sparkle; it sits before +, not at the bar's trailing end; it isn't shown pressed while open. ⌘J works; there's no single-key A and no command palette. |
| AI-15 | S3 | ui/panels/assistant.py:49-78,131-136 | Title "Assistant" is right, but the header holds a cog "AI Settings" instead of Clear Chat and ⋯ (there's no Clear Chat at all), the provider and model id show at the top, the empty state has no suggestion list, and the empty-key capsule reads "Connect an AI". |
| AI-16 | S3 | ui/panels/assistant.py:178-183 | The conversation is plain lines with bold "You" / "AI" / "Bodega" names, not accent bubbles and unbubbled answers; notices aren't tinted notes. |
| AI-17 | S3 | ui/panels/assistant.py:146-151 | Working shows "Thinking…" beside an indeterminate progress bar; no shimmer or glowing rim. |
| AI-18 | S3 | ui/panels/assistant.py:113-123 | A one-line field "Ask, or ask for a change" with a separate Ask button; no attach, no growing capsule, Send isn't inside it, Stop sits in the progress row, no Shift-Return, no dropping files. |
| AI-20 | S3 | ui/dialogs/ai_setup.py:55-95 | The key is always hidden (right), but there are Test and Load Models buttons instead of a key that checks itself on paste, models are shown by id, and Remove is a plain button beside the field rather than a red row at the card's foot. |
| AI-24 | S3 | ui/panels/assistant.py | No Copy under a message, and no Edit or Ask Again on the person's own messages. |
| T-05 | S3 | tests/screenshot.py:26, 82-87; tests/test_accent.py | Screenshots come in one appearance (dark offscreen), at one size (1600 × 1000), with the default accent: no light pass, no pale accent (Yellow is offered) and no WINDOW_MIN size. **Credit:** accent tests check every shade exists, on-accent ≥ 3:1, the stylesheet follows, the choice is saved and the default restores exactly. They don't check words at 4.5:1, a restart, or the canvas change. |
| T-13 | S3 | tests/test_window.py; tests/test_accent.py | Tests find things through Python attributes and private members, plus a few style objectNames (`StartTitle`), not component-owned test IDs. Actions are triggered by calling methods (`_pick`, `_open_editor`), not by role and visible words. |
| G-03 | S3 | CHANGELOG.md:1 | The changelog is release entries only. There is no start-here block (state, checks with expected results, next, quirks, how it ships, what the owner must supply) and no per-session entries (changed, decided, open, For the Standard). CHANGELOG feeds the release notes and the update window, so the session log needs its own file. |
| G-05 | S3 | git log; PR #10; CLAUDE.md:13 | CLAUDE.md says commit messages carry "nothing added after" the summary, yet 6 commits, both on this branch included, end in co-author and session lines naming the assistant, and PR bodies end in a session link. PR #10 bundles three features (28 files, +815/−218), and commits such as 97432d8, 665289e and the "Bodega 1.1.x" ones mix several topics. 19 early commits are under the owner's identity, and I can't tell who made them. |

## Not applicable

| ID | Why |
|---|---|
| V-10 | No red accent is offered ("Never red: red means late, failed or delete"). |
| V-21 | Bodega ships in English only; no right-to-left language. |
| V-29 | Not an installed web app. (The desktop window's title is "Bodega".) |
| V-43 | No touch input and no window narrower than 1280. |
| N-11 | No phone layout (desktop only, window at least 1280 wide). |
| N-12 | No phone layout. |
| N-13 | No phone layout. |
| N-19 | No organizations: profiles are letterheads and pricing for one person's data, not tenants; switching one changes no data. |
| N-20 | No sign-in. |
| N-21 | No permissions or feature switches hide places. |
| N-23 | The window never gets narrower than 1280, so the sidebar never needs to hide. |
| N-24 | No phone tab bar. |
| N-25 | No page with a period that sets its figures. |
| N-26 | No phone layout. |
| N-27 | No phone tab bar. |
| C-33 | No Home page. |
| C-36 | No charts. |
| C-41 | No notifications. |
| C-43 | No account service is connected; nothing to sign in to (see C-119). |
| C-52 | No imported document history. |
| C-56 | No command palette (see C-23). |
| C-57 | No Home. |
| C-62 | No Excel or CSV from the page window (CSV is a separate export of all gear). |
| C-63 | No dated list preview. |
| C-64 | Nothing loads from a server. |
| C-68 | No filter capsules (see C-16). |
| C-77 | Gear is counted in whole pieces; nothing is sold by fractions. |
| C-78 | No fill or pick states on rental lines. |
| C-79 | No per-line deals; a rental has one discount. |
| C-80 | No location figures. |
| C-83 | No self-applying rules. |
| C-84 | No deals. |
| C-85 | No free-goods deals. |
| C-87 | No variants (attached gear is a parent/child relation, see C-108). |
| C-89 | No fill or back-orders; availability is checked by pricing.shortages. |
| C-91 | No filter ranges. |
| C-93 | No lots. |
| C-94 | No posting; a rental's dates are its own. |
| C-95 | No shared capsules. |
| C-98 | No menu of several ticks (filter menus choose one). |
| C-101 | No drill-in menus (submenus instead, C-06). |
| C-103 | No column chooser (C-44). |
| C-104 | No server pages. |
| C-107 | Table rows have no ⋯ (a right-click menu instead; C-65). |
| C-116 | No date presets. |
| C-123 | No backend connection check. (The AI key check is AI-20.) |
| C-124 | No Home. |
| C-125 | No Home. |
| C-126 | No Home. |
| C-127 | No Home. |
| C-128 | No daily reports. |
| C-130 | No saved print layouts. |
| C-131 | No roles. |
| C-132 | No multi-document printing. |
| C-135 | No filter ranges. |
| C-136 | No reprint states. |
| C-137 | No presets. |
| C-139 | No charts. |
| C-141 | No tips. |
| C-142 | No final documents with money applied. |
| C-143 | No void. |
| C-147 | No restricted items. |
| C-148 | No back-orders. |
| C-149 | No deals. |
| C-150 | No credits. |
| C-151 | No credits. |
| C-152 | No payments in Bodega (invoicing is sent to Cobro/Saldo). |
| C-153 | No stock ledger; quantities are pieces owned. |
| C-154 | No reorder. |
| C-155 | No costing. |
| C-156 | No recurring templates. |
| C-157 | One person. |
| C-158 | No opening balances. |
| C-161 | No scrims. |
| C-169 | No touch calendar. |
| C-170 | Was N/A; now a Pass: the selection bar's capsules and its ✕ are all `control-h` (28), from tokens.SELBAR_* (components/panels.py SelectionBar). |
| I-22 | Bodega has no tabular paste: ⌘V outside a text field only pastes a photo onto the open piece. |
| I-27 | Bodega imports only a gear list (master data). It keeps no stock ledger, balances, purchase orders or rental history to switch over. |
| I-28 | No other system's stand-in records are imported: there are no promotions, deals or fake items to migrate. |
| A-04 | No sessions or timed steps: the account service is a stub that never signs anyone in, so nothing times out. Timed toasts are covered under A-11. |
| A-09 | Was N/A; now a Pass: single keys (N, E, D, /, ?, A) are on by default and Settings › Keyboard Shortcuts turns them off, while ⌘ and Ctrl shortcuts stay (window/menus.py SINGLE_KEYS, tests/test_keys.py). |
| D-13 | No tenants: one person's data in their own per-user folder. Profiles are that person's letterheads, not separate organizations. |
| D-14 | No accounts or roles: one person on their own computer and no server to check permissions (services/account.py is a stub that isn't connected). |
| D-17 | No server and nothing is served: photos and logos stay in the person's own data folder. |
| D-28 | No approvals: one person books their own rentals, and nothing waits for anyone's OK. |
| D-29 | No database and no permission seed. The one derived list, the shortcuts list, is read live from the menus. |
| D-30 | No permission keys or event types exist yet. The missing rental history is D-15. |
| D-33 | No migrations or database functions: older files are upgraded in memory by `from_dict` each time they're read (see D-11). |
| D-36 | No tenants, so there's no tenant key to leave blank: every write goes to the one data folder. |
| D-38 | No permissions or memberships (one person, no accounts). |
| D-39 | No capabilities: the one person can change every setting. |
| D-43 | The Cobro handoff writes a file into another app's folder on the same computer, with no account or key. AI uses the person's own key, by design (§14.6). |
| D-44 | Nothing syncs and there's no sales channel: Cobro gets a one-time draft that Cobro then owns. |
| D-46 | One person per data folder (the system user's own folder and keychain), so there are no tenants to key by. |
| D-47 | No syncing copy: one data folder, opened by one window at a time (the single-instance lock in app.py:44-80). Whether a shared folder should be supported is a question below. |
| D-48 | No server settings. The one typed address (AI "Other") is checked, and a bad one is reported as a setup mistake (providers.check_address). |
| D-50 | No reports over posted data (no sales or ledgers): the pages are current lists (inventory, rate card, labels) and each rental's own document, and preview, PDF, PNG and print already read one DocView. |
| K-01 | One person and one window (single-instance lock), so there's no second editor. The one writer that runs alongside, an AI job, works on copies, and each change is applied field by field only where the value hasn't changed since. Becomes applicable if a shared data folder is ever supported. |
| K-05 | No queued background jobs: every background task (AI, photos, prices, updates) is started by the person, shows progress and failure, can be stopped, and is safe to run again. |
| K-11 | No orders or invoices in Bodega: a rental is one document (quote → booked → out → returned) with no part-fills or back-orders, and billing is handed to Cobro. |
| K-13 | No stock that moves: what's out is worked out from rentals' dates and statuses (`units_out`, `shortages`), never typed in, and an item's qty is how many you own. Whether changes to that count should be recorded is an owner question. |
| K-14 | No payments in Bodega: billing and payment live in Cobro, and the deposit is a listed amount, not tracked. |
| K-15 | No invoices or credits in Bodega. |
| K-16 | No history from an earlier system: imports bring in gear lists only, and nothing is owed inside Bodega. |
| K-17 | One person makes every rental in the app (no imported or online rentals, and the assistant can't create one), and there's no approval step. |
| K-18 | No repeating rentals or templates: Duplicate makes a separate quote. |
| K-19 | No cost of goods sold: replacement value (what you paid plus tax) is for loss and insurance, not costing. |
| P-05 | No server. |
| P-06 | No database. |
| P-07 | No tenants and no shared caches: the caches in memory belong to one person's copy of the app. |
| P-08 | No endpoints. Tables paint rows straight from memory, without a widget per row; their speed is P-01. |
| P-10 | No server to overload. A provider's 429 is shown in plain words. |
| P-11 | No server or autoscaling. |
| P-12 | No tenants. |
| P-14 | No service to monitor, and by design Bodega sends nothing about how it's used (CONTRIBUTING rule 9). Errors go to bodega.log and crash.log in the data folder. |
| S-01 | No sign-in: the account service is a stub (`connected = False`, `REQUIRED = False`), so Bodega takes no passwords. |
| S-02 | No passwords are stored or checked; there is no account service. |
| S-03 | One person on their own computer; no one has access to other people's data through Bodega. |
| S-04 | No sign-in, so nothing to throttle. |
| S-05 | No sign-in, sign-up or reset. |
| S-06 | No one-time codes. |
| S-07 | Reset is a stub that says accounts aren't on. |
| S-08 | No sessions today. If accounts arrive, the session is already written to the keychain only, never a file (good groundwork). |
| S-09 | No sessions. |
| S-10 | No server, roles or tenants: one person, local files. |
| S-18 | No web server, pages or cookies; no embedded browser (QtWebEngine is excluded from the build). |
| S-19 | No server endpoints, so no CORS or CSRF. |
| S-24 | No sign-in, server or administrator to alert; shipping logs off the computer would break "nothing is sent". Update verification and blocked fetches are logged locally without secrets. |
| S-26 | No server routes. |
| S-27 | No organizations; only a person's own key. |
| S-28 | No servers configured, so Bodega rightly runs without an account. When accounts arrive, note that `REQUIRED` is a constant and the launch dialog can be closed: make sign-in unskippable then. |
| S-30 | No hosted deployments, previews, offline web cache or sign-out. Old GitHub Releases stay downloadable; the update check offers the newest. |
| S-31 | No server and no tenants; data never leaves the computer. |
| S-32 | No roles or memberships. |
| S-33 | No server routes or privileged keys. |
| S-34 | No user accounts; renters are contacts, not sign-ins. |
| S-35 | No one-time codes. |
| S-36 | No tokens. |
| X-02 | No server or public endpoint to put behind a CDN/WAF. |
| X-03 | No inbound endpoints; outbound calls run one job at a time. |
| X-04 | No server reading client addresses. |
| X-05 | No plans, accounts, trials or sign-ups; AI spend is on the person's own provider account (per-job limits under AI-07/AI-09). |
| X-07 | Bodega sends no messages itself: renter emails open in the person's own email app, feedback waits in an outbox, no SMS. |
| X-10 | Bodega has no public flows (no sign-up, coupons or server) for others to automate. It is itself the automation reading store pages, with a browser User-Agent: see Questions. |
| X-11 | No hosted storage or download links; files live in the person's own data folder. |
| X-12 | No invitations or sign-in email. |
| AI-02 | The chat runs on the person's own key on their own computer: nobody else can reach it to use it as a free chatbot. Its prompt is scoped to the gear list (tasks.py:438-444). |
| AI-10 | Only the key's owner can type into the assistant, on their own computer and bill; there is no other user to misuse it and no administrator to alert, and the provider's own policies apply to their account. Changes stay allow-listed and reviewed. |
| AI-26 | The assistant only answers about the gear list; it has no app links and is told nothing about places, Settings or commands, so there's nothing to keep in step. |
| AI-27 | The assistant never drafts a whole document (no rental or quote drafting). |
| AI-32 | No organization key; only the person's own. |
| O-06 | No hosted service to health-check or alert on, and by design nothing leaves the computer (no telemetry or crash reporting). The nearest equivalent, a packaged-build smoke test per platform, runs in CI (credited under O-01). |
| O-10 | No server and no shared build directory. Each CI platform builds into its own runner's `dist/`. |
| O-12 | No sign-in gate: `REQUIRED = False` and no account service is connected. This check applies once accounts are switched on. |
| O-14 | Not a web app: no service worker or installed web shell. Desktop updates are covered by O-08. |
| O-15 | No server connection to check: Your Data is a local folder and the account service is "not connected yet". |
| T-08 | Single person, local data folder, no tenants. |

## Passes

| ID | Sev | Evidence |
|---|---|---|
| V-01 | S2 | Glass only on the sidebar, the inspector (Dock) and Settings' sidebar; tables, cards and fields are opaque. |
| V-02 | S3 | Cards inside the glass panels are soft fills (`BLOCK`), not a second pane of glass. |
| V-03 | S2 | The bar has no border; the table's headings sit directly under it and stay there, so nothing ever shows between them (a hard edge), and content never passes under the bar. |
| V-05 | S2 | Every app color comes from a token with a light and a dark value; screenshots in both looks are complete. The printed paper is light by design (§4.15). |
| V-06 | S3 | In light the sidebar and inspector glass (#F3F3F6) are a step darker than the white page; in dark they are lighter (#2F2E30 over #1E1E1E), elevation by lighter surfaces. (There is no separate canvas and card surface in light: both are white; see V-26.) |
| V-07 | S3 | The look and accent are read from settings before the first window is built. |
| V-12 | S2 | Shortages carry an icon and words; statuses are words; toasts carry an icon and words. |
| V-20 | S3 | Share/export is an arrow out of a tray; no up/down arrow stands for export. |
| V-27 | S2 | Picking an accent restyles every window at once, menus included; an unknown key falls back to Bodega's blue. |
| V-30 | S2 | No accent edge bar on anything selected; the sidebar, Settings and table rows use a rounded fill. |
| V-31 | S2 | Nothing late shows no count rather than a red 0; shortages only appear when real. |
| V-34 | S3 | Monospace only for serial numbers on paper (literal codes read character by character); rental numbers, money and quantities use Inter. |
| V-38 | S3 | The sidebar is a fixed 232; the inspector is 27% of the window held between 360 and 420; nothing widens them. |
| V-39 | S2 | Every circle measured square (34, 24, 20, 18); the window never goes below 1280, so there's no phone width. |
| N-01b | S3 | Settings opens from the profile card and ⌘, and isn't a place. |
| N-07 | S2 | Nothing in the bar overlaps at any size the window allows. |
| N-08 | S3 | Lists (gear, kits, rentals), records in the inspector, Settings, the calendar (a list of rentals over time), the page window. |
| N-09 | S3 | A new piece, kit or rental left blank goes away. |
| N-10 | S2 | One pattern (split view); a record opens at its top (as of 665289e); the list keeps its scroll and selection beside it. |
| N-14 | S2 | Layout follows the window's width (the inspector's share); nothing scrolls sideways. |
| N-16 | S3 | Reopens where it was; one running copy (a second launch wakes the first); no second window by default. |
| N-22 | S3 | The trailing spot holds counts only. |
| C-02 | S3 | Verbs in Title Case with "…" where more input follows; OK only on an alert that just informs (common.notice). |
| C-05 | S1 | Slow work runs in a Worker with progress and Stop; its button is disabled while it runs. |
| C-07 | S3 | Menus, dropdown lists, pickers and the sidebar share one row height, inset and radius. |
| C-09 | S3 | A check column only where items are checkable; shortcuts only in the menu bar; titles start after their columns. (Context menus show no shortcuts.) |
| C-10 | S2 | Every context-menu command also exists in the inspector's ⋯, the Edit menu or the sidebar. |
| C-14 | S2 | Rows are drawn by QTreeWidget (no widgets per row); virtualized by the view. |
| C-15 | S1 | Names from people, sheets, the web and AI are shown as plain text. |
| C-18 | S2 | Visible Title Case labels above fields; placeholders are examples; typed text is never cleared. |
| C-20 | S2 | Money shows formatted at rest and bare while editing; the wheel never changes a value. |
| C-22 | S1 | Days are ISO dates without a zone; instants (checked out/in) are stamped by `now_iso`. |
| C-30 | S3 | Progress is determinate where known, with specific words and Stop. |
| C-35 | S2 | One layout for preview, PDF, PNG and print; paper always light; the profile's own color; page N of M; headings repeat. |
| C-40 | S3 | Opens on the place left; nothing asked up front. |
| C-46 | S3 | Straight 1-point dividers; only the highlight is rounded. |
| C-48 | S3 | ⋯ doesn't repeat the footer button; items that don't apply are hidden. |
| C-60 | S3 | No tall side columns. |
| C-71 | S2 | Every right panel is a SidePanel and every page uses the one toolbar. |
| C-74 | S3 | No tool's icon looks like another's; destructive buttons say what they do. |
| C-75 | S1 | Every word in any case (casefold), codes included, one filter per table. (Accents: C-24.) |
| C-81 | S2 | A new version is a window with Later and Update Now; it waits while another window is open. |
| C-86 | S3 | Check for Updates… in the profile card's menu (and the Bodega menu); says up to date or opens the update window. |
| C-92 | S1 | A line says what it takes: fees never touch availability; a kit takes its parts. |
| C-96 | S3 | Pop-ups show their value; ⋯ and + menus hold commands. |
| C-97 | S2 | Menus draw in their own layer and close on a choice, outside click and Esc. |
| C-99 | S2 | Arrows, Home/End, Return, Esc, focus back to the button. |
| C-102 | S3 | A combo's list is at least its field's width; nothing wider than the window. |
| C-109 | S3 | Turning chevrons open in place (group bands, sidebar); nothing uses › for that. |
| C-110 | S3 | The name edits in place where it is; nothing moves. |
| C-112 | S2 | A new rental starts with no renter ("Choose a Renter"). |
| C-113 | S2 | "New Renter…" is the last row of the renter list; Return never picks the first renter. |
| C-115 | S2 | A shortage warns and lets the rental go on. |
| C-118 | S3 | Long waits show their progress words. |
| C-121 | S2 | Every setting changes behaviour. |
| C-122 | S3 | Per-device (General) and per-profile (Profiles) settings sit apart. |
| C-133 | S3 | Signatures are blank lines on paper. |
| C-134 | S2 | The CSV carries value and rate as the bare numbers stored (MoneyField strips currency and separators). |
| C-140 | S3 | A lifted card with a count for several; the dropped rows stay selected; order is rewritten 1..n. |
| C-145 | S1 | A rental line keeps its name and price when the gear changes or goes. |
| C-146 | S2 | Whole pieces only; totals never add unlike units. |
| C-159 | S3 | Each list holds only its own kind. |
| C-162 | S3 | Esc closes Settings (no inner pages); nothing stacks on it. |
| C-165 | S2 | A band's chevron points right when closed and down when open; attached rows indent 18. (Its height: V-17.) |
| C-166 | S3 | Folded groups are remembered; a search opens what matches. |
| W-01 | S3 | The copy uses film-rental words (gear, piece, kit, renter, pickup, return, quote, booked). No record, entity, sync or payload words appear on everyday screens. "Records" shows up only in the user's own sense ("Kept for your records"). |
| W-07 | S3 | No gendered or ableist words. The person icon is neutral and avatars are initials. Default terms say "the renter", and the sample data is companies, not stereotyped people. |
| W-13 | S3 | Every place's name covers what it holds. Inventory holds gear and kits, Rentals holds every status plus the Calendar, and Coming Up holds quotes and bookings. Settings' General, Profiles, AI, Account, Keyboard Shortcuts and Your Data all match their contents. |
| I-05 | S2 | The only hover-only control, the sidebar section's +, has the same commands in the toolbar + and the File menu. Tooltip-only details also show elsewhere (a flagged line's reason shows when the line is opened, and calendar bars open on click). The toast stays while the pointer rests on it. Desktop only, so there are no touch gestures. |
| I-16 | S3 | No key badges on buttons, sidebar places or the search field. Keys appear only in menus, tooltips and the Keyboard Shortcuts list. |
| I-17 | S3 | The custom keys follow Apple: ⇧⌘N New Group, ⇧⌘I Import and ⇧⌘E Export are the standard pairs, ⌘/ is used rather than a shifted character, and no other modifier goes with a non-letter. |
| A-08 | S2 | The Settings › Account form is standard text fields: paste into the password field works (verified) and there is no puzzle. Password managers are unverified: the fields have no accessible names, and some managers rely on those. Sign-in itself is a stub, so check again once a service is connected. |
| D-09 | S2 | Every calendar day comes from `dates.today()`, the computer's local date, and there's no working-date override that could get stuck. Small gap: a window left open past midnight keeps yesterday's Late and Out Now until something refreshes. |
| D-19 | S2 | The only configuration is two environment overrides (`BODEGA_DATA_DIR`, `COBRO_DATA_DIR`) that fall back to the platform's per-user folders. AI, accounts and sending feedback are off until set up, and settings values are type-checked where they're read. |
| D-27 | S2 | Rental numbers are stored, compared and sorted as text through the one table comparison, and the next number reads the counting part by its numeric value, as §8.6 asks. Gear has no codes. |
| D-35 | S2 | Rental lines point at gear and kits by id (the name is kept only for gear that's been deleted), the renter is linked by id plus a deliberate copy for the agreement, and kits list their gear by id. |
| D-40 | S2 | The optional parts (the AI assistant and Send to Cobro) keep their own settings, nothing core depends on them, and turning AI off (removing the key) deletes nothing. |
| D-45 | S2 | Every picture is a file in photos/, re-saved under a random name and referenced by that name, with no data URLs in records; check-out photos keep their order. There's no stored alt text; the piece's name stands in for it. |
| K-08 | S1 | Panels change a record field by field as you type. AI changes and late photos write only their own field, and an AI change is skipped when that field changed while the job ran. |
| S-11 | S1 | The desktop equivalent holds: files are read through `from_dict` with known fields only, and AI changes are bound to an allow-list of fields (chat: group/name/brand/series). |
| S-12 | S1 | No SQL, no eval/exec/pickle (searched; Ruff's bandit rules run in CI). The updater's helper scripts quote every path (`shlex.quote`; double quotes on Windows, where a `%` in the install path would still expand, an edge case not under anyone else's control). |
| S-13 | S1 | Every QLabel is forced to plain text, tooltips go through `plain_tip`, AI answers are escaped, release notes are escaped before the tiny bold/link markup, rich text is used only for the fixed wordmark, and .ics fields are escaped. |
| S-14 | S2 | `safe_cell` prefixes cells starting with = + - @ tab CR (numbers like -50 stay); tested by `test_csv_export_cant_carry_formulas`. Probed edge cases behave. |
| S-15 | S1 | One fetcher for every address from data: https only, private/loopback/link-local/metadata and IPv6-wrapped private addresses refused, each redirect re-checked (max 5), connects to the checked IP, size and unpack caps, timeouts, no cookies. Fixed-host fetches (GitHub updates, docs.google.com export) use urllib directly and can't be aimed elsewhere. Note: the 15 s timeout is per read, so a server dripping bytes can hold a fetch for a long time (see X-06). |
| S-20 | S1 | AI keys and the session only in the OS keychain (no plaintext fallback; none bundled), sent only in headers, scrubbed from errors, never logged; tests prove keys stay out of settings.json and errors. Git history scanned here for key-shaped strings: none. Unverified: whether GitHub secret scanning and push protection are on (default for public repos; CI has no scanner of its own). |
| S-22 | S1 | People see plain messages and details go to the log; the bundle carries no .git, tests or env files. Small fix: `disable_windowed_traceback=False` means a crash during startup shows PyInstaller's traceback box; set it True. |
| S-29 | S1 | Seed data is made up (Juniper Lane Films, .example addresses, 555 numbers); no real customer data found in code or history. |
| S-37 | S2 | With no server, "saved on this computer only" is true by construction, and the safety notes Bodega shows are read from the real state (keychain available, feedback sender connected). The inaccurate AI data line is failed under AI-31. |
| X-09 | S1 | Each expensive or outward feature has the person's own switch: AI does nothing until set up and stops with Remove Key, the automatic update check can be turned off, Check Price runs only on a click; tested that jobs need setup. No remote global switch by design (see departures). |
| AI-04 | S1 | Every answer must fit a shape (allow-listed fields, `clean_text`, `clean_price`, `web_link`), wrong shapes are dropped, and answers are shown escaped with links off. Model-suggested links are fetched automatically, but only through core/web.py to verify them as §14.3 asks (see departures). |
| AI-05 | S1 | The model has no tools: it returns typed rows (`n`, field, value) checked against an allow-list, applied through the same Library calls as the interface (`put_in_group`, saves), as the one person who approved them. |
| AI-06 | S1 | Every change is shown old → new and ticked, applied only on Apply; each is bound to the old value it was made from (skipped if you edited it meanwhile); a copy of gear is kept first. Probed: one Undo reverted a three-change batch. |
| AI-12 | S2 | Model lists are read live from the provider, the chosen model is kept in settings, providers sit behind one adapter with two API kinds, and when a provider is down the feature says so in plain words while the rest of the app carries on. |
| AI-21 | S1 | The key stays in this computer's keychain only, never in settings or shared data; there's no server or organization; Remove Key takes it out. (No sign-out exists.) |
| AI-22 | S1 | No link in an answer is live: answers are escaped and the browser's links are off. Bodega offers no app links in answers (see AI-26). |
| AI-25 | S1 | Provider addresses are fixed in code and chosen by name; the model can never supply one; redirects are never followed. "Other (OpenAI-compatible)" takes the person's own typed address (https, or http only to this computer) with its own keychain entry, so another provider's key never goes there (see departures). |
| R-02 | S1 | No analytics or telemetry; AI is opt-in by connecting a key; the update check is part of the service and has a switch. The one pre-ticked box (version and kind of computer in feedback) carries nothing personal and nothing is sent yet; untick it by default to be spotless. |
| R-04 | S1 | Bodega puts nothing private in URLs it requests. The Email button builds a mailto: with the renter's address and the rental summary for the person's own mail app (if that's webmail, the text lands in browser history). No sign-in, so nothing to clear on sign-out. |
| R-06 | S2 | No analytics or error reports leave the computer; renters' details go to no outside service; feedback holds only what the person types and, if ticked, version and system. The AI provider is the person's own account and receives gear data, not personal data (list it in the inventory, R-01). |
| R-07 | S1 | The person can see, edit and delete everything in the app, export gear as CSV, back everything up as one zip, and open the data folder. |
| R-08 | S1 | No card numbers or payment details anywhere. |
| R-09 | S2 | Only times are stamped (checked out, checked in, created, updated); no actor trails, keystroke or location logging; the log holds counts, host names and file names. |
| O-02 | S1 | Workflow token is `contents: read`, with `write` only on the release job, and `persist-credentials: false` everywhere. The MACOS_*/APPLE_* secrets reach only the signing step, and the .p12 file is deleted by trap. Fork PRs get no secrets. Optional hardening: skip signing on `pull_request` and delete `build.keychain` after use. |
| O-03 | S2 | One `__version__`. A hand-pushed tag that doesn't match it fails CI, and main auto-tags only an untagged version. All 10 tags on origin (v1.1.0 to v1.2.1) match their commit's version, and no number was reused. Small gap: CI doesn't check that CHANGELOG has a section for the version, so release notes can silently be empty (scripts/release_notes.py:44-46). |
| O-08 | S1 | **Credit:** checks on every launch (switchable) and offers an update window that waits for no other window. An "Update to X" button sits in the sidebar, and Check for Updates… is in the menus. The download must come from this repo's releases, match size and GitHub's SHA-256 digest (no digest, no install), and a signed Mac app must be replaced by the same Team ID. Hash failures are reported in the dialog. **Residual gap:** a Mac signature or swap failure in the helper script after quitting is not reported, and Bodega just doesn't reopen. That path is dormant while the Mac build is unsigned. |
| O-13 | S3 | How releases actually ship is written in the instructions file read first every session: merging an untagged version releases it, the build tags it, the names are a contract, and the tag must match. Host-account and merge-method constraints don't apply to GitHub Actions. It isn't in a changelog start-here block, which doesn't exist (see G-03). |
| T-02 | S2 | No retries, xfail or quarantine. The two skips are platform guards (Linux/Mac helper on Windows). One conditional `pytest.skip` depends on the sample's shape and would silently switch the drag test off; make it an assert. |
| T-07 | S1 | The security rules are tested. The guarded fetcher refuses private and IPv6-mapped addresses, redirects and DNS re-pointing. Also tested: unpacking caps, a hostile-HTML parser, CSV formula escaping, refused oversized sheets, plain-text names, keys never in settings, errors or redirects, ids that could name other files, and updates only from our releases with a checksum. Per-endpoint and other-tenant authorization is N/A: no server, no tenants. |
| T-10 | S2 | Best judgement from a sample, since nothing records it. The five regression tests from the two newest fixes (97432d8, 665289e) all fail against their parent commit (one by segfault) and pass on the fix. The rule "see it fail first" is not written in CONTRIBUTING. |
| T-17 | S3 | Qt's offscreen platform draws the app's own scroll bars, so screenshots show them. Unit tests also assert scroll-bar behaviour: a panel opens at the top, and a two-line name doesn't scroll inside its box. |
| G-04 | S1 | No secrets, keys, real emails or phone numbers in any commit. The only matches are `.example`/`evil.com` test addresses and the 555 sample numbers. core/sample.py is made up, the docs screenshots show only the sample, and the standard is not in the repo or its history. The owner's personal gmail is the author email on 24 commits (see Questions). |

## Decisions to record in the Project Addendum

Proposed departures, each needing the owner's yes before it goes into the addendum's table (some are already listed
there as proposed):

- **Desktop only, pointer only** (§3.6, §3.7, Appendix G phone and touch; T-04, T-11, T-18 phone parts): no phone,
  tablet or touch layout; the window stays at least 1280 × 700.
- **One person, local files** (§8.9, §11, §12.2–12.4): no organizations, accounts, permissions or server; two writers
  prevented by the single-instance lock. Profiles are letterheads, not tenants.
- **Autosave with full undo** for gear, kits and rentals (§6.5), saving 400 ms after the last change (§9.3 says 1–2 s;
  add the maximum wait); explicit Save kept for renters, profiles and check-in.
- **The title in the bar's row** at its leading edge (§3.3 allows it for a desktop window).
- **The session log outside CHANGELOG.md** (§18.3): CHANGELOG.md becomes the Release text and the update window, so
  "start here" and per-session entries live in their own file.
- **Billing lives in Saldo** (formerly Cobro): Bodega makes draft invoices and holds no invoices, payments or
  credits, which is why the payment and credit checks are N/A.
- **Imports only add** (§6.6): curated gear is never overwritten; pieces are matched by name and department, since
  gear has no codes.
- **A rental keeps its own copy of the renter**, and only quotes and bookings follow edits to the saved renter.
- **No usage telemetry and no remote switches** (§13.8, §15.8): nothing leaves the computer except AI requests the
  person makes, the update check and link fetches; the AI kill switch is Remove Key.
- **Model-suggested links are fetched to check them** (§14.3), only through `core/web.py`.
- **"Other (OpenAI-compatible)" takes a typed address** (§14.9): https anywhere, plain http only to this computer,
  with its own keychain entry.
- **Serial numbers in monospace on paper** (§2.7).
- **Day rates rounded to whole dollars** (a pricing rule in `core/pricing.py`), and money without cents on gear lists
  (a display choice §8.7 needs recorded).
- **Python naming** (snake_case) for §8.15's case table; line length 110.
- **Logs in the data folder** (`<data>/logs`), so Back Up and Open Data Folder include them.
- **Appearance switch** (Match System first and default, Light, Dark) outside a native Apple app.
- **Unsigned builds until certificates exist** (S-23), with updates checked by SHA-256.

## Questions for the owner

Questions 1 to 7, 16, 22 and 27 are answered (in [PROJECT_ADDENDUM.md](PROJECT_ADDENDUM.md), "Decided", with who
and when). Bodega is a desktop app, so the standard's checks for web browsers and servers don't apply (the owner);
where a question below has a clear answer in the standard about how Bodega looks or is built, the standard's answer
is followed.

**Answered first** (they decided how the business works, so the S1 fixes waited on them):

1. **When does a rental's price lock**: when it's booked, or when it goes out? After that, should it change only
   through a recorded Reopen? (K-12)
2. **Rental numbers**: may a deleted rental's number ever be used again (today it is)? Should a quote keep its number
   when its date moves into another year? Do you want a Next Number setting, so a series from your old spreadsheet
   carries on? (C-51, D-07, D-24)
3. **Deleting**: should rentals that are out or returned be deletable, or only cancellable? And gear that rentals
   point to: delete, or Retire? (C-111, C-117, §4.25)
4. **Booking gear that's already promised**: block it, ask you to confirm, or keep the quiet hint (sub-renting may
   make overbooking normal)? (K-04)
5. **Import**: should "Use the Sheet's Pricing" start off, and may Bodega fill blanks (company, quantity 1, for rent)
   without asking? (I-24)
6. **Send to Cobro**: change it to Send to Saldo, writing into Saldo's folder? Should a second send update the draft
   or make a new one, and should each profile remember which Saldo profile it sends to? (D-16, D-32, K-02)
7. **Commits**: every commit is yours, and its message a plain summary with nothing after it? (G-05, D-22)

**Then, when you can:**

8. Rental status: picked by hand from the dropdown, or set only by Check Out / Check In (Cancelled by hand)? (C-129)
9. Are 8.25% sales tax, a 4% day rate and a 10% deposit your own numbers, or should a new profile start blank? (D-37)
10. **Answered: as the standard has it.** An address has its street, city, state, postal code and country. (C-82)
11. Will the Bodega folder ever live in Dropbox or iCloud for two computers? (K-01)
12. Back Up: add Restore…, and offer a password (backups hold renters' details)? (O-07, R-05)
13. May people go back to an older Bodega? If so, files need a format version. (O-04)
14. How long should renters' details stay on old rentals? (R-03)
15. Before a big AI job, may Bodega say how many requests it will make and stop after a few failures? What ceiling?
    Should AI setup suggest a spending limit and name providers whose free tiers may keep what's sent? (AI-07, X-08)
16. **Answered: Bodega says it's Bodega.** It used to tell stores it was a web browser (`core/web.py`).
17. SVG logos: turn them into PNG when added? (S-17)
18. The update check runs at every launch; its note says once a day. Which is meant? (S-25)
19. **Answered: as the standard has it.** N, E, D, /, ? and A work alone outside text fields, with a switch in
    Settings › Keyboard Shortcuts to turn them off; ⌘1 to ⌘4 are gone (the sidebar is grouped). (I-12, I-13, A-09)
20. English and US formats only, or prepare for translation? (W-05, W-08)
21. **Answered: as the standard has it.** The menu bar shows on Windows and Linux too. (N-15, I-04)
22. **Answered: as the standard has it.** What Undo can take back is done at once, with "Deleted. Undo"; Return does
    the action you chose, and the safe choice when the loss is a side effect. (C-27, C-28)
23. **Answered: as the standard has it.** A Check Price problem stays under the link until it's closed. (W-06, A-11)
24. Earned and Paid Off: show them as estimates ("≈")? (W-19)
25. **Answered: a desktop app.** Rules for web pages (reflow at 320 points) don't apply. (A-02)
26. Protect main so a pull request merges only once its four builds are green? (O-01)
27. **Answered: yes, later.** Code signing (an Apple Developer ID, a Windows certificate), not wanted yet. (S-23)
28. Dependabot security updates and GitHub secret scanning: on? Take the closed dependency bumps? (S-21, S-20)
29. The standard stays only on your machine (standard §18.4). Sessions in the cloud start from a fresh clone and won't
    have it unless you attach it. Is that how you want it?
30. Commit email: keep your personal address as the author email on a public repository, or switch to GitHub's
    private noreply address? (G-04, G-05)

## This round

- **What changed**: this report; [PROJECT_ADDENDUM.md](PROJECT_ADDENDUM.md) (identity, platforms, vocabulary, domain,
  integrations, limits, AI, process, proposed departures); CLAUDE.md now points at the standard and the addendum and
  says the standard is kept out of the repository (excluded through `.git/info/exclude`). No app code changed.
- **What was decided**: none of the departures yet (they wait for the owner); the standard's copy stays excluded
  locally rather than named in `.gitignore` (§18.4); this round's commits are plain summaries.
- **What's open**: the questions above; then the fixes in the order above, in small changes that each stand alone.
- **For the Standard** (general lessons this audit taught):
  - A desktop app needs a short translation table for the server checks (migrations → file format versions,
    "leave-page question" → asking before quitting, deploys → releases and rollback); several checks were judged by
    analogy and a stated translation would make audits agree.
  - The audit template's "Audited by" line meets §18.5's rule against naming tools; say what goes there.
  - §18.3's changelog conflicts with apps whose CHANGELOG is shown to their users (release notes, an update window):
    the standard could name a separate session log as the default.
  - A probe beats reading: three S1 findings (a repriced returned rental, a reused number, a lost edit after a failed
    save) were only certain once run on throwaway data. Part 19 could say "verify every S1 by running it".
  - Offscreen measurement needs the window to opt out of fitting the screen (Qt's offscreen screen is 800 points);
    worth a line in §17.4 for desktop toolkits.
