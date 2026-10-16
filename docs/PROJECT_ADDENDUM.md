# Project Addendum: Bodega

The owner's Universal App Standard is what Bodega must follow (how it looks, behaves and is built). This file is
everything the standard leaves to each app, and every place Bodega departs from it, with the reason. Anything not
written here uses the standard's default.

Standard version followed: 1.5 (2026-10-16). Measured against it: [STANDARD_AUDIT.md](STANDARD_AUDIT.md).

Where the standard lives: on the owner's machine, never in this repository (standard §18.4). A working copy may sit
at `docs/UNIVERSAL_APP_STANDARD.md`, excluded locally through `.git/info/exclude`; a fresh clone won't have it, so
ask the owner for it.

## Identity (§2.11)
- Name, as written everywhere: **Bodega**
- Wordmark and icon: "bodega." in Inter Bold with the full stop in the accent; the app icon is "b." on a dark tile,
  the full stop in sky blue, drawn by `scripts/make_icon.py`
- Accent color: **Blue**. Light `#2F6FDB`, dark `#4A90F7`, on-accent white. Not a red, so the red rule doesn't apply
- People pick their own accent: **yes**, in Settings › General (Blue, Purple, Pink, Orange, Yellow, Green, Turquoise,
  Graphite). Never red: red means late, failed or delete
- Organization color: each profile's **Paper Color** (Sky Blue, Chile Red, Dusk Violet, Turquoise, Marigold, Sage,
  Ink), used on everything printed
- Light theme neutrals (§2.3): plain neutral whites and greys today; tinted from the accent is a standard default not
  built yet (audit V-26)
- Display font for large titles: Inter Display (bundled with Inter); monospace: IBM Plex Mono, for serial numbers on
  paper only
- Family of apps: Bodega stands alone (standard, "Each app stands alone"); it names another app only for its one real
  integration (below)

## Platforms and sizes (§3.7)
- Platforms shipped: **macOS** (Apple silicon and Intel), **Windows**, **Linux**. A desktop app (PySide6, Qt
  Widgets), installed from GitHub Releases. No web, phone or tablet version
- Input: a pointer. The pointer sizes of Appendix A apply everywhere; there is no touch or phone layout
- Breakpoints: the window never gets narrower than 1280 × 700 (`tokens.WINDOW_MIN`), so the phone and narrow
  breakpoints never apply
- Detail pattern: **split view** (§3.5). The picked thing opens in a glass panel at the trailing edge, 27% of the
  window held between 360 and 420
- Places: **Inventory** (All Gear, with each group under it; Kits, with each kit under it) and **Rentals** (All
  Rentals, with Out Now and Coming Up under it; Calendar). The profile card sits at the sidebar's foot. No phone tabs

## Vocabulary (§5.1)
- Words we use: gear, a piece (of gear), group, kit, rental, quote, booked, out, returned, cancelled, renter,
  profile, day rate, replacement value, agreement, Check Out, Check In, attached ("what goes with it")
- Words we never use, and what we say instead: client or customer → **renter**; business → **profile**; package →
  **kit** (packages stay the word in code and stored files); item → **piece** or **gear**; record, entity, sync →
  never in the interface
- Date format: "Oct 18, 2026" and, in date fields, "Sun, Oct 18, 2026"; ranges "Oct 18–25, 2026"
- First day of the week: Sunday
- Currency and number formats: each profile's currency sign (default "$"), US separators (`core/money.py`)
- Languages: English only

## Domain
- **What the app is**: a film-gear rental house's inventory and rental desk, for a filmmaker who rents out their own
  gear or a small rental house. It keeps every piece with its value, quantity, serials and photos; groups it;
  builds kits; prices rentals from the replacement value; checks gear out and in; and prints agreements, quotes, an
  inventory, a rate card, kit sheets and labels.
- **Tenancy model**: none. One person's data folder on one computer. A **profile** is a letterhead with its own
  pricing and terms (a person can have several), not a tenant: every profile sees the same gear, kits, renters and
  rentals.
- **Roles and capabilities**: one person, no roles, no sign-in.
- **Consequential transitions** (confirmed or recorded): deleting gear, a kit, a rental or a profile (confirmed);
  Check Out marks a rental Out, Check In marks it Returned (each with its checklist and time stamp); a rental's
  number, once printed, identifies it to the renter.
- **Documents** (§4.15): rental agreement and quote, inventory, rate card, kit sheet (Letter, portrait); gear labels
  (Avery 5160, 30 to a Letter page, with a QR code). The paper's accent is the profile's Paper Color; paper is always
  light.
- **Business rules and where each lives** (§8.2): every price, day count, total and availability rule in
  `core/pricing.py`; rental numbering (PREFIX-YEAR-001) in `core/store.py`; earnings in `core/earnings.py`; service
  reminders in `core/maintenance.py`; check-out rows in `core/checks.py`.
- **Open decisions** (§18.2): the rest of the list at the end of [STANDARD_AUDIT.md](STANDARD_AUDIT.md) ("Questions
  for the owner"). Answers are recorded below, with who decided and when.

### Decided (the owner, 2026-10-16: "whatever is industry standard" where marked)
- **A rental's prices lock when it's booked** (industry standard). A quote follows the current day rates, kit prices
  and the profile's pricing; once a rental is Booked (and while Out, Returned or Cancelled), every line keeps the rate
  and name it had then. Changing a rate afterwards never rewrites it.
- **A rental number is never issued twice** (industry standard). A deleted rental's number stays spent; a rental
  keeps its number once it has one (a new date in another year doesn't change it); a typed number that another
  rental already has is said in the field; each profile has a Next Number so a series from an older system carries
  on.
- **Rentals that are booked, out or returned aren't deleted**: they're cancelled, and kept. Only a quote can be
  deleted. **Gear that rentals point to is retired**, not deleted (delete stays for gear nothing points to).
- **Booking or checking out gear that's already promised asks first** ("Book Anyway?"), rather than blocking:
  sub-renting can make it deliberate.
- **Send to Cobro is Send to Saldo** (Cobro's new name), writing into Saldo's data folder.
- **Nothing mentions AI or the tools used to build Bodega** in commits, pull requests, release notes or documents;
  the app's own AI features (the Assistant, AI Settings) are the exception.

## Integrations (§8.11)
| System | Direction | What it owns | Credentials |
|---|---|---|---|
| **Saldo**, once Cobro (the owner's invoicing app) | Out: a rental becomes a draft invoice, written into Saldo's `invoices/` in its format (`services/saldo.py`); the rental remembers it, and sending again updates the draft | The invoice, its number and payment | None (a local folder) |
| Google Sheets | In: a sheet shared by link is downloaded as .xlsx and imported | The sheet | None (a public share link) |
| GitHub Releases | In: the update check and download | Bodega's releases | None |
| AI providers (Anthropic, OpenAI, Gemini, Kimi, OpenRouter, DeepSeek, Mistral, xAI, Groq, or a custom address) | Out: the gear asked about, in | Nothing; answers are proposals | The person's own key, in the system keychain |
| Store and maker web pages | In: Check Price and photos from a link (`core/web.py`) | The page | None |

## Limits and money (§13)
- Cost drivers and their caps: the person's own AI spend (each answer capped at 4,096 tokens, 90 s; 150 questions
  a job, stopping after 3 failures in a row; spend caps are
  the provider account's own); web fetches (15 s, 6 MB, https and public addresses only)
- Rate limits per endpoint group: none (no server)
- Quotas per plan: none (no plans)
- Upload types and sizes: photos and logos are read and saved again (PNG/JPG/SVG for logos), scaled to 1,600 points
  on the long side; spreadsheets .xlsx, .xlsm, .csv
- Spend caps: the AI provider account's own, set by the person
- Kill switches: AI is off until a key is set; removing the key turns it off

## Security and privacy (§12, §15)
- ASVS level target: not applicable (no server); the desktop rules of §12.11 apply
- Sign-in methods; second factor: none today (the account service is a stub)
- Session idle / absolute timeouts: none (no sessions)
- Data inventory location: the data folder (gear, kits, rentals, renters, profiles, settings, photos, logos, logs);
  AI keys in the keychain
- Regulations that apply: none known (renters' names, emails, phones and addresses are kept only on this computer)
- Retention periods: kept until the person deletes them

## AI (§14)
One block per feature (`services/ai/tasks.py`). Every feature is off until the person sets a key, runs on that
person's own provider account, and changes nothing until approved in Review. What each request sends: the gear
involved, up to 600 pieces per request, with each piece's name, company, series, group, quantity, status, what it cost
and what goes with what. Renters and rentals are never sent. Every answer is capped at 4,096 tokens, with every
provider; a job asks at most 150 questions (it says how many before a big one) and stops after 3 failures in a
row. Gear lists and pages are marked as data, never instructions, in every prompt.

- **Update from Links**. Purpose: read a piece's product page (or, when a store refuses, another page found and
  checked) for a price and a tidier name. Proposes: name, company, series, price paid. Must refuse: anything but those
  pieces' details.
- **Find Missing Links**. Purpose: a product page for gear without a link; every link is fetched (through
  `core/web.py`) and matched before it's suggested. Proposes: links (and a price for gear without one). Must
  refuse: a link that isn't https, isn't public, or whose page isn't about that piece.
- **Tidy Up Names**. Purpose: consistent names. Proposes: name, company, series. Must
  refuse: anything else (a blank never replaces what was typed).
- **Organize Groups**. Purpose: sort gear into sensible groups. Proposes: groups. Must refuse: anything
  else.
- **Assistant** (chat). Purpose: answer questions about the gear and make changes asked for. Proposes: group, name,
  company, series only. Must refuse: any other change (prices, links, quantities, deleting), and anything about
  renters or rentals, which it never sees; its prompt says the gear list is data, never instructions.
- Model and provider: the person's choice (Anthropic, OpenAI, Gemini, Kimi, OpenRouter, DeepSeek, Mistral, xAI, Groq,
  or another OpenAI-compatible address). Quotas: none yet beyond the caps above. Kill switch: Remove Key.

## Process (§18)
- Commit attribution rule: **no tool, assistant, co-author or session lines**, in commits and pull requests alike. A
  commit message is a short plain summary, nothing added after it (CLAUDE.md). Decided by the owner, 2026-10-16.
- Where the standard lives: excluded locally (above).
- Test commands and their expected results: `ruff format . && ruff check . && python -m pytest -q`: no changes,
  "All checks passed!", every test passing.

## Departures from the standard
Each needs the owner's yes before it counts; until then the standard's rule stands and the audit row stays a Fail.

| Section | What we do instead | Why | Decided by, when |
|---|---|---|---|
| §3.3 Bar | The page's title sits in the bar's row at its leading edge (not a large title under the bar) | The standard allows it for a native desktop window; one choice, on every page | Already the app's pattern; confirm |
| §3.6, §3.7, App. G phone and touch | No phone or touch layout; the window stays at least 1280 × 700 | A desktop tool used at a desk beside a gear cage | Proposed, needs a yes |
| §18.3 Changelog | `CHANGELOG.md` holds only what people will notice, by version (it becomes the release notes and the update window's text); the session log ("start here", per-session entries, For the Standard) goes in its own file | The update window shows CHANGELOG entries to everyone using Bodega | Proposed, needs a yes |
| §2.3, §4.12 Appearance | Settings › General offers Match System, Light and Dark, Match System first and default | Bodega is drawn by Qt, not by AppKit; the standard allows the switch outside a native Apple app | Proposed, needs a yes |
| §2.7 Monospace | Serial numbers print in IBM Plex Mono | Serials are copied and compared character by character (0 and O, 1 and I) | Proposed, needs a yes |
