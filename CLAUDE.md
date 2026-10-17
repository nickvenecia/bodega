# Bodega: notes for working on the code

Cross-platform (macOS / Windows / Linux) gear inventory and rental app.
Python 3.12 + PySide6 (Qt Widgets). Pages are drawn with QPainter (one layout for preview, PDF, PNG, print).
Shipped as a PyInstaller app; GitHub Actions builds the downloads.
The owner is a filmmaker (director/DP/editor/colorist), not a full-time developer. Explain changes in plain words.

## Read these first
- **[docs/SESSION_LOG.md](docs/SESSION_LOG.md)**: where things stand ("Start here"), what each session changed and
  left open.
- **The owner's Universal App Standard** is the destination for how Bodega looks, behaves and is built: Apple first,
  every value from its Appendix A and G. It is the owner's own document, kept out of the repository: a working copy
  sits at `docs/UNIVERSAL_APP_STANDARD.md`, excluded through `.git/info/exclude` (never commit or push it). A fresh
  clone won't have it: ask the owner for it before any change it governs.
- **[docs/PROJECT_ADDENDUM.md](docs/PROJECT_ADDENDUM.md)**: what the standard leaves to Bodega (accent, platforms,
  vocabulary, integrations, AI) and every departure from it, with the owner's yes. Follow the standard and the
  addendum; where this file or DESIGN.md disagrees with them, they win, and the difference is a fix to make (see
  **[docs/STANDARD_AUDIT.md](docs/STANDARD_AUDIT.md)** for what doesn't meet it yet).
- **[docs/OVERVIEW.md](docs/OVERVIEW.md)**: what's built today, measured at a named commit (gaps and drift said
  plainly); **[docs/SCOPE.md](docs/SCOPE.md)**: what Bodega builds, what Saldo and other apps own, what's put off.
  Check the scope before adding a feature.
- **[DESIGN.md](DESIGN.md)**: how the app and the paper look and read. All app values live in `bodega/ui/tokens.py`;
  paper colors in `bodega/core/looks.py`. Never type a size or color anywhere else.
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: code rules.
- Before finishing any change: `ruff format . && ruff check . && mypy && python -m pytest -q`.
- Commit messages: a short plain summary, nothing added after it.

## Layout
```
bodega/
  core/            Gear, packages, rentals. No Qt imports.
    model.py       Item (brand = company, series, qty, serials, value, day_rate, parent = what it goes with,
                   extras = parts added by hand), Package + PackageLine, Client (a "renter"), Business (a "profile": pricing + terms), Rental + RentalLine (lines may
                   have their own pickup/return); from_dict() reads every field through one
                   shared reader (_read: plain values coerced, broken lists skip the record), keeps fields from a
                   newer Bodega (`newer`), reads an unknown status as the cautious one (CHOICES)
    pricing.py     THE pricing rules (see its docstring): replacement value, auto day rate, stock() (a gear sheet's
                   totals), with_attached() (attached gear, shared out across the parent's units, rounded up),
                   packages, billed days (week_days, weekend deal, typed billed days), line_dates/line_days
                   (lines with their own dates), totals(),
                   periods(); availability: bookings() per line window, shortages() (busiest-day sweep), out_now()
    importer.py    .xlsx (openpyxl) / .csv in: header found by its words, headings -> departments / groups,
                   rate % and tax from formulas; attach_guesses() ("… for Sony FX6" -> the FX6, by model-name tokens,
                   compared with what each item IS = its name before "for"); write_csv() out (round-trips);
                   cell hyperlinks and =HYPERLINK() become Item.link; download_google_sheet() (export as .xlsx)
                   Known: what's in Bodega already, by name, the sheet's old name, link or serial (match())
    document.py    build_rental / build_inventory / build_ratecard / build_package / build_labels -> DocView
                   (labels: a sticker per unit, QR "bodega:<item id>", item_from_code() reads a scan) (every string on the
                   page); agreements group lines by date range when they differ; summary_text() for email
    store.py       Library: gear.json, packages.json, rentals/<id>.json, clients.json, businesses.json, settings.json;
                   atomic writes, unreadable files set aside, a write that fails kept in `unsaved` (save_again(),
                   on_unsaved tells the window, why_unsaved says why); numbering
                   PREFIX-YEAR-001, never given twice (settings "numbers": the last given in each series;
                   set_next_number, number_taken); delete_item detaches what was attached and leaves rentals the name;
                   groups() in your order (settings "group_list"), add/rename/remove/step, put_in_group()
                   (what goes with it comes along, emptied groups go), apply_groups(); pricing() never None;
                   save_rentals() writes many rentals side by side (WRITERS); `who` (the signed-in account's name,
                   set by the window) is stamped on each history line and Check Out / Check In tick, blank without one
    backups.py     safety copies (backups/: one a day, and before an import, Tidy Up, AI changes or a restore)
                   and Restore: read_backup() checks a zip as untrusted, put_back(); Library.restore() keeps a copy
                   first and every number spent; photos and logos are only ever added
    svg.py         SVG logos as untrusted: clean() keeps only the drawing (no outside pictures, links, scripts,
                   DOCTYPE); every SVG logo is drawn through doc/render.svg_logo, which cleans it
    settings.py    every setting in settings.json with its kind and default (DEFAULTS); value() reads one safely
    terms.py       an agreement's words: DEFAULT_TERMS ({owner} = profile name), DEFAULT_NOTE, terms_for()
    errors.py      what went wrong, in plain words: plain(e, "save the PDF"), the computer's reasons by errno,
                   a short reference (logged) for anything unknown
    addresses.py   an address: street lines, city, region (its code, from the country's own list: REGIONS),
                   postal code, country (blank: HOME); region_code() refuses a region not on the list,
                   region_from_postal(), lines() as printed (an old one-box address prints as typed);
                   countries.py the ISO list
    search.py      folded(): case and accents off, so "cafe" finds "Café"; words(), matches()
    tidy_renters.py  Tidy Up Renters: proper() case by rule (business words kept), changes() shown first;
                   Library.tidy_clients() applies them (a safety copy, bookings follow)
    pageopts.py    how a page prints (C-53, C-61): PageOptions (paper, letterhead, note, a list's columns and
                   filters), for_page() (your last choice, else the profile's default), kept(), reading_key()
    tidy.py        Tidy Up Groups: GROUPS, RULES (by name), RENAMES (by old group); suggest(), changes()
    prices.py      Check Price: fetch a product page, read its price (JSON-LD offers, price meta tags). Stores
                   may block it; that's web.Refused, with a plain message
    looks.py       paper palettes (light for every export, dark for the preview's Dark Page) + accent colors
    sample.py      the made-up Juniper Lane Films rental house (tests, smoke test, screenshots)
    earnings.py    what each piece has earned: its share of Out/Returned rentals (by own day rate), coming (Booked),
                   paid_off()
    figures.py     the figure row above each list: gear(lib, group), kits(lib), rentals(lib) -> [Figure] (a slice
                   filters the list when pressed; a tone colours the number only); a record's strip: piece(), kit()
    maintenance.py service reminders: Item.service_days after the last "service" in Item.log; due(), needs_service()
    checks.py      Check Out / Check In rows: pieces() a rental sends out, rows() kept ticks/notes/photos, progress()
    ics.py         rentals as a calendar file: pickup + return events per date range, stable UIDs, SEQUENCE grows
    history.py     undo/redo: History.mark() after saves and refreshes keeps the state before each change;
                   undo()/redo() put a state back and save it (window state and settings aren't undone)
    update.py, paths.py, log.py (JSON lines; no renter or profile names, no full paths), net.py, fileutil.py, dates.py, money.py   shared helpers
    web.py         safe web fetching for anything a link points at: https only, public addresses only (checked
                   on every redirect, connecting to the checked address), size caps, a linear HTML reader
                   (read() -> PageInfo); image_of() a page's main picture, fetch_image() pictures only, whole or
                   refused; web_link() is THE test of "is this a web link"; site_name() ("B&H"); Refused: a store
                   that lets only web browsers in (B&H). Bodega never disguises itself to get past one: the app
                   offers another way in (copy the photo in the browser, paste it)
  doc/             render.py: layout(DocView, Palette, logo) -> [Page]; paint(); label sheets are Avery 5160
                   (30 to a Letter page), QR codes via segno. fonts.py, export.py
  services/        Outside Bodega, no Qt. Each has a plain interface and a "not connected yet" default.
    secrets.py     the system keychain (keyring): AI keys and the account session; never a file, never logged
    ai/providers.py  PROVIDERS (Anthropic, OpenAI, Gemini, Kimi, OpenRouter, DeepSeek, Mistral, xAI, Groq, custom);
                   two API kinds (anthropic, openai); Setup (settings "ai"); list_models() live, never hardcoded;
                   ask()/ask_json(); keys never on a redirect, plain http only to this computer
    ai/evals.py    the AI's naming, grouping and planted-instruction cases, scored against a real model
                   (`python -m bodega cli ai-eval`; CI runs it when the secret BODEGA_EVAL_KEY is stored)
    ai/usage.py    METER: every question counted (day, month, tokens), a daily limit (settings "ai_daily_limit":
                   warns at 80%, LimitReached at 100%), at most 20 a minute; the window loads and saves it
    ai/tasks.py    update_from_links (a link that's Refused: another page, found and checked as find_links does),
                   find_links (every link fetched and matched before it's suggested: _checked_pages), tidy_names,
                   organize_groups, chat (an answer, plus changes asked for: group/name/brand/series only); Change/Result; clean_text/clean_price validate everything; apply() (snapshot first)
    account.py     AccountService (sign_in / sign_out / reset_password) + REQUIRED; plug a real service in with use()
    saldo.py       Send to Saldo (once Cobro): a rental as a draft invoice written into Saldo's invoices/ in its
                   format (numbering ported from saldo/core/numbering.py; never sets Saldo's files aside, never
                   writes before Saldo has opened once or into Cobro's old folder); Rental.saldo_invoice: sent
                   again, it updates that draft; Business.saldo_profile: asked once; the window asks to quit Saldo
    feedback.py    Feedback, an outbox in the data folder until a FeedbackSender (or ADDRESS) is connected
  ui/
    style/         tokens.py (every size, color, timing; DARK/LIGHT swapped by tokens.use(scheme, accent); ACCENTS the accent
                   choices, accent_set() builds one's shades), theme.py (the QSS,
                   icons, theme.font(), theme.qcolor(), plain_tip())
    components/    address.py (AddressFields: the one address control, on renters and profiles),
                   photos.py (gear photos: keep() reads and saves every picture again into photos/, scaled to
                   PHOTO_MAX_PX; from_link() takes a product page's main picture through core.web; a picture
                   pasted (Copy Image in a browser) or dropped: picture_file/image/link, has_picture; thumbnails),
                   panels.py (LeftPanel: every list of places on the left, with NavRow; SelectionBar: while rows are
                   ticked; SidePanel: every panel on the right, one header: title, round buttons, ⋯, ✕ at the far
                   right),
                   widgets.py (Card, Disclosure, Section, TitleEdit, IconLabel, SearchField, button_row, fields…,
                   Toast: MainWindow.toast(text, tone) with "done" / "problem" / "" for news; Banner: a problem
                   that lasts, across the top; Guarded: a form with its own Save asks Discard Changes / Keep
                   Editing before dropping typing, and says what "changed" means), glass.py
                   (GlassRoot backdrop drawn once and reused; Dock: the inspector floats and slides, the content
                   makes room through the row's right margin, a Table slides as two pictures: freeze/thaw),
                   sheet.py (every dialog shows over its window: prepare() as it's made; the window blurred and
                   dimmed behind, a ✕ level with its title, a click outside closes it unless SHEET_OUTSIDE = False;
                   Settings is SHEET_KIND = "window"; still() the blurred picture), access.py (the system's Reduce
                   Motion, Increase Contrast, Reduce Transparency: every
                   animation asks duration()/reduce_motion(); tokens.use(contrast=, opaque=)),
                   hover.py (hover's lift on the accent-filled controls: LiftEffect, a touch larger over a soft
                   shadow while hovered; the app's event filter calls hovered()),
                   rows.py (Group: grouped rows, G.12: a name, a card of rows, a note; value(), control(),
                   switch(), action()),
                   scrollbars.py (Style: Fusion with the standard's scroll bars: over the content, shown while
                   scrolling, gone SCROLL_HIDE_MS after; kept, with their room, where the system says Always),
                   datefield.py (DateField: typed or picked from its month popover, the standard's G.22),
                   empty.py (EmptyPage: where a table would be with nothing in it: a title, a line, one button;
                   empty gear takes a dropped spreadsheet),
                   figures.py (FigureRow: core/figures' tiles above a list, G.10.5; FigureStrip: a record's
                   figures under its head, divided by hairlines, G.17),
                   titlebar.py (Mac: macOS moves the window; double-click fills the screen or shrinks it, animated
                   via NSWindow setFrame:animate:), worker.py (Worker: background jobs with progress and stop;
                   every thread is a Background: let go of, never destroyed mid-run, when its window goes)
    window/        main_window.py (MainWindow: building, navigation, opening, size and place) made of parts: menus.py
                   (and SINGLE_KEYS: N E D / ? A), groups.py, editing.py, transfer.py (import, export, back up),
                   pages.py (the page window), services.py (settings, account, feedback, updates, light/dark), ai.py
                   (assistant, jobs, review, apply); common.py (kind_of, TITLES); sidebar.py (Inventory: All Gear with
                   its groups, Kits with each kit; Rentals: All Rentals with Out Now and Coming Up, then Calendar, then Renters;
                   rows fold, kept in settings "sidebar_folded"; a folded All Rentals still shows out/late; at the bottom:
                   your profile card (its menu: your profiles, Send Feedback, Check for Updates, Settings)); tables.py
                   (GearTable, KitTable, RentalTable, RenterTable, each in its ListCard (G.10.1); a tick column first (TICK: the ticks are the selection, a click
                   opens, chosen_ids() what's ticked), the gear grip last; COL_W widths; never per-row widgets; gear
                   that goes with a piece is one level under it (G.11): open_pieces, kept in settings "gear_open",
                   family ticks, listed_rows() for ticks and showing_rows() for what you see); lift.py
                   (Lift: drag by the grip, drawn live: rows slide apart to show where it lands; off to the left it
                   becomes a normal drag for the sidebar's groups); filters.py (FilterButton + GearFilter: divide by,
                   show, company, missing, Clear Filters); calendar_view.py (CalendarPage: Month, a wall calendar with
                   bars, or Timeline; settings "calendar_mode")
    panels/        base.py (DetailsBase: header ⋯, footer_button(text, icon), Cards), item.py (gear: the head
                   (photo beside the TitleEdit name, the status line, company · group), Details / Value & Rate / added parts; Check Price; Update with AI),
                   kit.py (TitleEdit name, About, Gear, Price), rental.py (LineEditor per line…), renter.py
                   (RenterPanel: the Renters page's right side, the renter's form (dialogs/client.py, embedded,
                   Save Changes) and their rentals; a new renter is still the sheet), assistant.py
                   (AssistantPanel: the AI chat and jobs, in the right-hand panel; toggled by its button or ⌘J)
    dialogs/       common.py (Alert: confirm and notice, Return says yes; ask_name, tidy_preview, about),
                   palette.py (Search Everything, ⌘K: places, records by core/search's *_hay, the menus' commands),
                   checklist.py (CheckDialog: tick, scan, note, photos, each kept as made; Mark as Out / Returned),
                   shortcuts.py (Settings › Keyboard Shortcuts, read from the menus); ProfileDialog and SignInDialog
                   are Embeddable (widgets.py): the same form stands alone or sits in Settings, settings.py (Settings:
                   a glass sidebar of sections that edit in place, in grouped rows (components/rows.py); one window
                   at a time), ai_setup.py (AISettings: Settings › AI, each change kept as it's made),
                   ai_review.py, account.py (sign in), feedback.py, import_sheet.py, page_options.py (the page
                   window's options: grouped rows beside the pages, each change redrawn),
                   gear_picker.py, preview.py (the page window), profile.py, client.py, update.py
  app.py           QApplication, fonts, stylesheet, rounded popups, every QLabel plain text, one window at a time,
                   use_text_size() (Settings › Text Size or the computer's, as Qt's scale, before the app starts),
                   restart(),
                   Python's cycle collector only on the window's thread, between events (_MainThreadGC),
                   --smoke-test
  cli.py           `python -m bodega cli sample OUT.pdf --doc agreement|quote|inventory|ratecard|package`,
                   `python -m bodega cli import SHEET.xlsx OUT.pdf`,
                   `python -m bodega cli update-check` (offline: finds this build's own update file),
                   `… cli update-from FILE` (a packaged copy updates itself from a release file: CI, each build
                   from its own download)
scripts/make_icon.py   draws bodega/assets/icon.png from its one vector source, icon.svg ("b." on the dark tile, the
                       full stop in the accent; `--source` writes the SVG again from the font and tokens)
scripts/release_notes.py   a Release's text: the version's CHANGELOG entries, then the downloads
scripts/lock.py        requirements.lock (every build, every computer) and requirements-lint.lock, with hashes
tests/screenshot.py    QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR [SHEET.xlsx]
```

## Rules that matter
- **Never lose gear or a rental.** Every write is atomic (`store.write_json`); unreadable files are renamed aside.
- **A save that fails is said until it works**: the banner and Not Saved in the profile card, tried again every
  SAVE_RETRY_MS; quitting over it asks (MainWindow.may_quit). Every form with its own Save is a `Guarded`.
- **The preview is the export.** Everything goes through `render.layout` + `render.paint`; only the Dark Page differs.
- **Pricing lives in core/pricing.py only.** The UI and documents ask it; never compute a rate or a day count elsewhere.
- Attached gear: `Item.parent` is the item it lives with. Always walk it with `pricing.with_attached` / `root_of`
  (both guard against loops). Attaching copies the parent's department and group.
- Rental lines are compared by identity (`rental_panel._index`), never `==` (two lines can be equal).
- A line has its own dates only when `Rental.own_dates(line)`; blank dates mean the rental's.
- Renters are saved only on purpose (the renter's form: its sheet, or on the Renters page with Save Changes).
  Rentals keep their own copy; quotes and bookings follow edits.
- New model fields need defaults that mean "off"/empty: old files are read through `from_dict()`. A change to a
  file's shape (a renamed field) raises `store.FORMAT`, with a step in `store.UPGRADES` and a test for it.
- Personal details and real gear lists never go in the code or the repo (it's public). Use core/sample.py.
- Imports are absolute (`from bodega.core import pricing`), one module per job; no Qt in core/ or services/.
- **Anything a link points at goes through core/web.py** (fetch, web_link). Never urllib a URL from data directly.
- **Every photo goes through ui/components/photos.keep()** (read and saved again; never a file kept as it came).
  Photo files are never deleted with a piece (undo and copies may still use them).
- **Every error a person sees goes through core/errors.plain(e, "what was being done")**: never `str(e)` of the
  computer's own error. Status lines are widgets.status_line() (a screen reader hears them change).
- **Secrets only through services/secrets.py** (the keychain). Never in settings, files, logs or error messages.
- **An AI's or a web page's words are data.** They pass tasks.clean_text / clean_price, are shown as plain text
  (labels are plain app-wide; tooltips through theme.plain_tip), and change nothing until approved in Review.
- Deleting gear or a kit keeps every rental's price (store._hold_rental_prices / _keep_rental_prices).
- Changes that are more than a typed field go through one store operation each: `attach`, `detach`, `retire`,
  `set_status` (stamps out/returned), `import_items`, `restore`, `delete_items`, `delete_rental`.
- Only a quote is deleted (`Rental.deletable()`); a booked one is cancelled (`cancel_rental`). Gear rentals point to
  (`store.rentals_with`) is retired, with what's attached. A rental's `history` is only added to (store._note_history
  on save; `Rental.happened()`). Booking or marking out over a shortage asks (`may_hold`).
- Broken records are skipped and their file kept aside (store.set_aside); ids must pass store.safe_id.
- Every change to gear, kits, rentals, renters, profiles or groups must end in flush() or refresh() (that's
  where undo marks it). New commands go in the menus with their standard key (the shortcuts list reads them).
- Every left list is a components.panels.LeftPanel and every right panel a SidePanel: subclass them, never
  build a panel's frame by hand.
- **Act once the click is over.** A tile, a sidebar row or a line item a refresh can rebuild never opens a window or
  a menu inside its own click (CONTRIBUTING rule 16): the window can throw it away mid-click, which crashes Bodega.
  A part of a window thrown away while the window stays open is hidden first (rule 17).
- One popup at a time: a window never opens another on top (Settings edits in place; Review and alerts are
  the exceptions, and close before anything else opens).
- Every number in the UI is a token; every font comes from theme.font(); dialogs end with widgets.button_row().
- Every list of choices (menus, dropdowns, pickers, suggestions) uses the LIST_* tokens (the standard's G.7:
  corners 14, inset 6, rows 32 with corners 8); the sidebar and Settings' sections are the same rows in the glass
  (NAV_*). Never a list with its own sizes.

## Commands
```bash
pip install -r requirements-dev.txt
python scripts/lock.py                    # after changing requirements*.txt: the hashed locks CI installs from
python -m bodega
python -m pytest -q
QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR
pyinstaller bodega.spec --noconfirm
BODEGA_DATA_DIR=/tmp/x python -m bodega   # a throwaway data folder
```

## Releasing
Merging is releasing. A pull request with a change users will notice also bumps `__version__` in
`bodega/__init__.py` (patch for fixes and polish, minor for a new feature; one bump per pull request, however many
commits) and puts its CHANGELOG entries under that version (never "Unreleased"). When main has a version with no
tag yet, the build tags it `vX.Y.Z` and publishes the Release; the owner only merges. A pushed tag still works, and
the build refuses one that doesn't match `__version__` (an app reporting an older number offers itself as an update).
The Release's text is that version's CHANGELOG entries (scripts/release_notes.py), and the update window shows them:
write them in plain words, for the people using Bodega.
CI attaches Bodega-mac-apple-silicon.dmg, Bodega-mac-intel.dmg, Bodega-windows-setup.exe, Bodega-windows-portable.zip,
Bodega-linux-x64.AppImage, Bodega-linux-x64.tar.gz. **These names are a contract** (README links + update.asset_name).
update.REPO = "nickvenecia/bodega"; the repo must stay public.

## Questions waiting for the owner
Listed, with what each one decides, in docs/STANDARD_AUDIT.md ("Questions for the owner"; answered ones move to
docs/PROJECT_ADDENDUM.md with who and when) and docs/SESSION_LOG.md. Don't decide them in code: ask.

## Ideas not done yet
- Live Google Calendar sync (needs a Google Cloud project, OAuth, and Google's app review); today it's an .ics file
- Purchase date and depreciation for taxes
