# What's Built

What Bodega is today, measured, not what it's meant to become (that's the owner's Universal App Standard and
[PROJECT_ADDENDUM.md](PROJECT_ADDENDUM.md); what doesn't meet it yet is in [STANDARD_AUDIT.md](STANDARD_AUDIT.md)).
Where this and the standard disagree, this says how things are and the standard says where they're going.

**Measured at** commit `56a9232` on the branch `claude/awesome-bohr-9d9eva` (version 1.3.0, not merged or
released yet; main is 1.2.1), 2026-10-16. Later changes add a dated note at the end instead of rewriting this.

## What it is

A desktop app (Mac, Windows, Linux) for a small film-gear rental house, or a filmmaker who rents out their own kit:
an inventory of gear, kits made of it, and rentals that go from quote to booked to out to returned, with the
paperwork for each. One person on one computer; everything is kept in files in its own data folder. Python 3.12 with
Qt Widgets (PySide6), shipped as a packaged app with nothing else to install.

## Places and screens

- **The window**: a sidebar of places on the left, a list in the middle, the open record in a panel on the right.
  - Places: **All Gear** (and each group of gear under it), **Kits** (and each kit), **All Rentals** with **Out Now**
    and **Coming Up**, and the **Calendar** (Month, or a Timeline). Your profile card sits at the foot.
  - Each list: a row of figures about all of it (some filter it when pressed), filters showing as capsules, sortable
    headings, a tick on every row and a selection bar for what's ticked, search, and an empty page with ways to start.
  - Each record's panel: a head (photo, name, number and status, a line of detail, a strip of figures), Print and ⋯
    in one capsule with the record's next step beside it, then its cards. A pager steps through the list.
- **On top of the window** (one at a time): the page window (a rental's agreement or quote; a kit's sheet; the
  inventory list, rate card and labels); **Settings** (General, Profiles, AI, Account, Keyboard Shortcuts, Your
  Data); Import Spreadsheet; Review (approving what the assistant suggests); Search Everything (⌘K); Check Out and
  Check In (a checklist with scanning, notes and photos); a renter; a profile; the update window; Send Feedback.
- **The assistant**: a panel on the right for questions and jobs (naming, grouping, finding links and prices),
  using the person's own AI provider and key; nothing it suggests changes anything until approved in Review.

## Records and where they're kept

The data folder holds `gear.json`, `packages.json` (kits), `rentals/<id>.json`, `clients.json` (renters),
`businesses.json` (profiles: pricing and terms), `settings.json`, `photos/`, `logos/`, `backups/` and a log. Every
write is atomic; a file that can't be read is set aside, never overwritten. A safety copy is kept each day and
before any big change, and File › Restore… brings one back.

## Rules, and where each lives

- **Pricing** (`core/pricing.py` only): replacement value with tax, the automatic day rate, kits (a discount or a
  fixed rate), billed days (week and weekend deals, or typed), lines with their own dates, totals, deposits.
- **A rental's life** (`core/model.py`, `core/store.py`): quote → booked → out → returned, or cancelled. Only a quote
  can be deleted; prices hold once it's booked; a number is never given out twice; its history is only added to.
- **Gear on rentals**: availability per day, shortages asked about before booking or marking out, gear that's on a
  rental retired instead of deleted, attached gear that travels with its piece.
- **Saving honestly**: a failed save is said until it works and asked about before quitting.

## Integrations

- **Saldo** (the owner's invoicing app): Send to Saldo writes a draft invoice into Saldo's own folder.
- **Calendars**: Add to Calendar writes an .ics file; nothing syncs live.
- **Spreadsheets**: .xlsx and .csv in (a Google Sheet by its link, too), .csv out.
- **The web**, only when asked: a product page's price (Check Price) and photo, and GitHub for updates. Some stores
  refuse anything but a browser; Bodega says so and offers another way.
- **AI providers** (Anthropic, OpenAI, Gemini and others, or one on this computer): the person's own key, kept in
  the system keychain, with a daily limit.
- **Not connected yet**: accounts and sign-in, and sending feedback (it waits in an outbox).

## How it's built and shipped

CI tests and builds all four downloads (Mac Apple silicon and Intel, Windows, Linux) from hashed locks, audits every
package, and attaches a software bill of materials. Merging to main is releasing. About 600 tests, with screenshots.

## Known gaps, and drift in the other documents

- **CI on Windows** doesn't finish yet: the test machine stops answering partway (being tracked down file by file).
  Linux and the Apple silicon Mac pass; the Intel Mac crashed in the tests until today's fix. (Fixed since: see the
  end.)
- The standard's larger redesigns not made yet are listed in STANDARD_AUDIT.md ("After the fixes"): among them text
  that follows the system's text size, attached gear folding under its piece, print options, one table for every
  menu's commands, and dialogs as sheets.
- The downloads aren't signed (an Apple Developer ID and a Windows certificate are the owner's to get, later).
- **Drift**: DESIGN.md describes the look as of 1.2 in places; where it differs, the standard and
  PROJECT_ADDENDUM.md win. README's screenshots are today's.

## Since then

- **2026-10-16, later**: CI passes on all four builds (both Macs, Windows and Linux), tests and downloads; the
  Windows test machine's stall was a test named by 2 MB of its own bytes, and the Mac crashes were Qt objects kept
  past their life. The Windows installer is built with a pinned Inno Setup (6.7.1). A row's right-click menu and its
  panel's ⋯ come from one list of what the record can do. Gear that goes with a piece is folded under it in the gear
  list (it opens in place, sums up what's with it, and its tick ticks all of it).
