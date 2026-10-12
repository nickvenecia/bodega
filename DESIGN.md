# Bodega design rules

The rules for how Bodega looks and reads. They are Listo's and Cobro's rules (the three apps are siblings), with the parts that are only about video or invoices swapped for gear and rentals. Follow them for every screen, dialog and control.
If a change needs something these rules don't cover, add a rule here in the same commit.

All numbers and colors live in **`bodega/ui/tokens.py`**. The stylesheet (`bodega/ui/theme.py`) and
every widget import from there. **Never type a size, spacing, font size or color anywhere else.**
If you need a value that doesn't exist, add a token, give it a comment, and add it to the tables below.

---

## 1. Sizes

### Controls: one height for everything you click or type in

| Token | px | Used for |
|---|---|---|
| `CONTROL_H` | 34 | **Every** button, dropdown, text field and segmented control |
| `SMALL_H` | 24 | Chips on file cards, naming token buttons, icon-only buttons |
| `INDICATOR` | 16 | Standard icon box |
| `TOGGLE_ROW_H` · `TOGGLE_W`×`TOGGLE_H` | 32 · 36×20 | An on/off row and its switch |
| `BAR_H` | 6 | Progress bars |
| `TRACK_H` / `HANDLE` | 4 / 14 | Slider groove / handle |
| `SCROLL_W` / `SCROLL_MIN` | 10 / 30 | Scrollbar width / shortest handle |

- A button, a dropdown and a text field side by side must line up exactly. Never set a height on
  a single control; the stylesheet already sets it.
- Buttons size their width to their text (padding `0 SPACE_3`). Don't give buttons fixed widths.
- Dropdowns and text fields in the sidebar stretch to the full column width.

### Icons

| Token | px | Used for |
|---|---|---|
| `ICON_SM` | 14 | Icons inside small buttons (scissors, info, close) |
| `ICON` | 16 | Icons inside normal buttons and menus |

All icons are line icons drawn as SVG in `theme._SVG` and made with `theme.icon(name, color)` (buttons, menus) or
`widgets.IconLabel(name, tone)` (an icon that isn't a button). Both follow light and dark by themselves; never draw
an icon once with a color and keep the picture. Add new icons there; don't load image files for UI icons.

### Fixed layout sizes

`SIDEBAR_W`, `INSPECTOR_W`, `TOOLBAR_H`, `SEARCH_W`, `TABLE_ROW_H`, `NAV_H`, `ROW_INDENT`, `TEXT_BOX_H`, `TEXT_BOX_TALL`, `TEXT_BOX_TERMS`,
`NUM_FIELD_W`, `QTY_FIELD_W`, `LOGO_THUMB`, `PAGE_GAP`, `PAGE_SHADOW`, `DIALOG_W` (and `DIALOG_W_WIDE`, `DIALOG_W_XWIDE`),
`PROFILE_DIALOG_H`, `PICKER_SIZE`, `PAGE_DIALOG_SIZE`, `CAL_*`, `DAY_W`, `WINDOW_SIZE`, `WINDOW_MIN`, `COL_W` (every
table column), `MENU_ROW_H`, `NAV_GAP`, `ROW_INSET`, `NOTES_H`. Timings too: `DOCK_MS`, `SAVE_DELAY_MS`,
`TABLE_DELAY_MS`, `TOAST_MS`, `UPDATE_CHECK_DELAY_MS`, `QUIT_WAIT_MS`. Use these names, never the numbers.

**Fonts:** one family (Inter, `looks.FONT`, shared with the paper), loaded once in `app.py`. Every size is a
`TEXT_*` token in pixels and every weight a `WEIGHT_*` token; in code, make a font with `theme.font(size, weight)`,
never `QFont()` or `setBold`.

---

## 2. Spacing: a 4-point grid

| Token | px | Use it for |
|---|---|---|
| `SPACE_1` | 4 | A label and its control; an icon and its text; lines inside one item |
| `SPACE_2` | 8 | Related items: buttons in a row, cards in the list, checkboxes in a stack |
| `SPACE_3` | 12 | Between sections inside a panel |
| `SPACE_4` | 16 | Padding of panels, bars and the main areas |
| `SPACE_5` | 24 | Padding of dialogs, empty states |

- Build layouts with the helpers in `bodega/ui/widgets.py`:
  `vbox(widget, margins, spacing)` / `hbox(...)` (spacing defaults to `SPACE_2`),
  `combo(...)` for dropdowns, and `Section("Title")` for a labelled group (Title Case label + its controls, `SPACE_1` apart).
- Margins are `SPACE_*` tokens or `0`. Nothing else.

---

## 3. Type

Font for the app itself: **Inter** (bundled in `bodega/assets/fonts`). One family only.
The paper uses Inter too, plus IBM Plex Mono for serial numbers (see §9).

| Token | px | Used for |
|---|---|---|
| `TEXT_XS` | 11 | Chips |
| `TEXT_SM` | 12 | Section labels (`MUTED`, semibold), secondary text: file details, hints, tooltips |
| `TEXT_MD` | 13 | Body text and every control (the default) |
| `TEXT_LG` | 14 | Emphasis: renter names and amounts on cards, department names, footer totals |
| `TEXT_XL` | 18 | Dialog titles, empty-state headlines |
| `TEXT_BRAND` | 21 | The "bodega." wordmark only |

Weights: `WEIGHT_REGULAR` 400 for text, `WEIGHT_MEDIUM` 500 for controls,
`WEIGHT_SEMIBOLD` 600 for titles, labels and the primary button, `WEIGHT_BOLD` 700 for the wordmark and dialog titles.

---

## 4. Corners

| Token | px | Used for |
|---|---|---|
| `RADIUS_XS` | 4 | Small inner corners |
| `RADIUS_SM` | 6 | Chips, menu and list rows, small buttons |
| `RADIUS` | 8 | Buttons, fields, dropdowns, segmented controls |
| `RADIUS_LG` | 12 | Package and rental cards, line boxes, popups and menus |

Menus and dropdown lists are **always rounded**, with transparent corners, and so is the highlighted
row inside them. `app._RoundPopups` handles this for every `QMenu` and dropdown automatically: it makes
the popup window see-through and gives every dropdown `widgets.ComboItemDelegate` (rounded highlight,
`MENU_ROW_H` rows, thin separator lines). Don't create popups that bypass it.

---

## 5. Color (dark and light)

Bodega follows the computer's light or dark setting (View → Appearance to pin one). Every color token has a
dark and a light value (`tokens.DARK`, `tokens.LIGHT`); `tokens.use()` swaps them and `theme.apply()` rebuilds
the stylesheet. So: read colors as `tokens.X` when drawing, never copy one into a constant at import time.
Icons made with `theme.icon()` redraw themselves; the table refills. The table below lists the dark values.

**The accent is yours to pick** (Settings › General › Accent Color: `widgets.AccentPicker`, settings "accent";
empty means Bodega's own blue). `tokens.ACCENTS` lists the choices (never red); `tokens.accent_set()` builds
every accent shade from one color for dark or light, with dark words on the accent wherever white wouldn't read.
The blue's shades are hand-set in `DARK` / `LIGHT`. The app icon and the paper keep their own colors.

| Token | Use |
|---|---|
| `BG` | Window background |
| `PANEL` | Sidebar, footer, dialogs |
| `CARD` / `CARD_HOVER` / `CARD_SELECTED` | Cards and gear rows (normal / hover / selected), text fields |
| `RAISED` (+ `_HOVER`, `_PRESS`) | Buttons, popups |
| `WELL` | Sunken areas: the preview behind the paper |
| `BORDER` / `BORDER_STRONG` / `BORDER_HOVER` / `BORDER_CHECK` | Hairlines, control borders, hover, empty checkbox |
| `TEXT` / `MUTED` / `FAINT` | Main text / secondary text / hints, labels, disabled |
| `ACCENT` (+ `_HOVER`, `_PRESS`) | Blue (red is never an accent: it means late or delete). Selection, the one primary action, focus |
| `ON_ACCENT` | Text and icons on the accent (and on a Late chip) |
| `ACCENT_OFF` / `ACCENT_OFF_TEXT` | A disabled primary button |
| `ACCENT_TINT` / `ACCENT_EDGE` | Blue wash and outline (the Booked chip, the selected card, an open fold count) |
| `GOOD` / `WARN` / `BAD` | Returned / out or in repair / late or double-booked. |
| `PAPER` / `SHADOW` | The paper and its shadow in the preview |
| `BAD_TINT` / `BAD_EDGE` | Danger button hover / a failed card's outline |

- The accent means "selected" or "do this". **One** Primary button per view (Save PDF…, Save, Import Spreadsheet…).
- Status color comes from data, not code: `widgets.set_tone(w, tone, text)` with "quote" | "booked" | "out" |
  "late" | "returned" | "cancelled" | "repair" | "retired". The stylesheet maps tone to color.
- Never call `setStyleSheet()` on a single widget. Add a rule to `theme.STYLESHEET`
  under an object name instead.

---

## 6. Components

Use an object name to pick a style (`btn.setObjectName("Ghost")`). These are the only variants. Every text
button is a capsule CONTROL_H tall; every icon button is a circle:

| Kind | Object name | When |
|---|---|---|
| Primary button | `Primary` | The single main action in a view (Save PDF…, Save, Import Spreadsheet…) |
| Normal button | *(none)* | Everything else (Print…, Add Gear…, Edit…, Cancel, Show File) |
| Quiet button | `Ghost` | Small helpers inside a card (Suggest, Use Profile Terms, Select All / None) |
| Add button | `AddChip` | "+ Add Gear" at the end of a list in a card |
| Danger button | `Danger` | Destructive actions in a form (Delete Profile…, Delete Renter…): the normal shape, red words |
| Alert's yes | `DangerFill` | Only the destructive button of an Alert (Delete) |
| Link | `LinkBtn` | Inline text links (Get a Key ↗, Forgot your password?) |
| Round icon button | `widgets.circle_button()` (`#Circle`, `#CirclePrimary` for New) | Every icon button in a toolbar or a panel header (✕, ⋯, filter, ‹ ›): round, raised, CONTROL_H. **Must** have a tooltip |
| Small icon button | `widgets.icon_button()` (`#IconBtn`) | Icon buttons inside a row or card (a line's ⋯): round, no frame until hovered |
| Left panel | `panels.LeftPanel` (+ `NavRow`) | Every list of places on the left (the sidebar, Settings): rows `NAV_INSET` from the glass, corners `NAV_R` (concentric) |
| Right panel | `panels.SidePanel` | Every panel on the right (details, assistant); `header_icon()` for its own round buttons |
| Panel header | `widgets.PanelHeader` + `add_close()` | Every right-hand panel: title at the left; round ⋯ (or ⚙), then the round ✕ at the far right, `SPACE_4` from every edge |
| Status chip | `Chip` (QLabel) | Quote / Booked / Out / Late / Returned / Cancelled on a rental; Out / Repair / Retired / Not for Rent on gear |
| Sidebar row | `sidebar.NavRow` (`#Nav`) | A place: All Gear, a department, Kits, Out Now, Coming Up, All Rentals, Calendar. A count on the right |
| Table | `tables.Table` (`QTreeWidget#Table`) | Gear, kits, rentals: `TABLE_ROW_H` rows, sortable columns, attached gear folds under a chevron |
| Where it is | `QPushButton#Where` | Top of the gear panel when the piece is out or booked; click opens that rental |
| Dropdown | `widgets.combo(items, current)` | **Every** pick-one setting, however few choices. Put extra detail in the item's tooltip |
| On/off setting | `widgets.ToggleRow` | Every on/off setting: one full-width row, label left, switch right, whole row clickable |
| Section | `widgets.Section` | Every labelled group in the details panels and dialogs |
| Multi-line text | `widgets.TextBox` | Addresses, notes, terms (`TEXT_BOX_H`, `TEXT_BOX_TALL`, `TEXT_BOX_TERMS`) |
| How many | `widgets.qty_field()` | Every quantity: a typed whole number, arrow keys count up and down |
| Date | `widgets.date_field()` | Every date (calendar popup, "Sun, Oct 18, 2026") |
| Card | `widgets.Card` (`#Card`) | Every group in an inspector panel: a soft `BLOCK` tint, `RADIUS_LG`, `SPACE_3` inside, a `#CardTitle` |
| Fold-away group | `widgets.Disclosure` | A Card whose title folds it away (kits, rentals, the profile dialog); folded, it says what's inside |
| A big name | `widgets.TitleEdit` (`#BigName`) | The name of the piece or kit at the top of its panel: a title that wraps, editable in place |
| Dialog buttons | `widgets.button_row()` | The bottom row of every dialog: right-aligned, the main one last, `SPACE_4` below the content |
| Your own things | `widgets.picker()` + an `Edit…` button | From (your profiles) and Renter (your renters): the dropdown picks, Edit… beside it opens the details |
| Rental line | `rental_panel.LineEditor` | A header row (what it is, its amount, ⋯) that folds its fields away. One open at a time |
| Picking gear | `gear_picker.GearPicker` | Search and tick: attaching, filling a package, adding to a rental |
| Long one-line text | `widgets.ElidedLabel` | Text that may not fit (gear names!): cut short with "…", the full text in its tooltip |

Choosing a control:
- Pick one setting → **dropdown**, always, even with only 2–3 choices. Status, From, Renter, Belongs To, Priced By,
  A Week Bills As and Paper Color are all dropdowns. Build them with `widgets.combo` / `set_combo`.
- The result of a choice is shown once, in the live preview, not repeated under every option.
- Actions that belong to a dropdown (Add a Profile…, New Renter…) go **inside** that dropdown, below a separator.
- A dropdown of your own things that have details of their own (profiles, renters) also gets an **Edit…** button
  right beside it. That's where people look for it; an "Edit" hidden inside the list went unfound.
- Menus open from icon buttons (⋯) with `InstantPopup`; the menu arrow is hidden.

---

## 7. Words

Bodega talks like a helpful person, not like software.

- **No explaining on screen.** No hint sentences under fields, no paragraphs in empty states or dialogs. If a label
  needs explaining, change the label; if it still does, a short tooltip. Show a section only when it has something
  in it (an item on no rentals has no On Rentals section).
- **Less at once.** One line per gear row (name, how many, rate). Departments fold. Details groups other than the
  basics start folded and say what's inside.

- **Fewer words.** Labels and section titles are 1–4 words ("Name taken", not "If that name is already taken"). If something needs explaining, put it in a tooltip, not on screen.
- Plain language: "Belongs To", not "Parent asset". "Paid Each", not "Unit acquisition cost". "Mark as Booked", not "Update status".
- **Title Case for labels**: section and group names, buttons, checkboxes, tabs, menu items, dropdown
  choices, dialog titles and card states ("Its Own Dates", "Mark as Booked", "Weekend Counts as 1 Day").
  Small words stay lowercase inside a label (a, an, the, and, or, of, to, in, on, at, for, by, with, as, per);
  acronyms and file things stay as they are (PDF, PNG, A4). No ALL-CAPS labels in the app (the paper's small
  capital labels are part of the paper's design, §9).
- **Sentences stay sentences**: tooltips, hints, placeholders, error messages and toasts
  ("Goes wherever the Sony FX6 goes: in packages, on rentals and agreements.").
- Buttons are verbs ("Save PDF…", "Show File"). Use "…" when the button opens a dialog or file picker.
- Errors say what happened and what to do, without jargon: "Bodega can't read logo.gif. Use a PNG, JPG or SVG file."
- Promise safety where it matters: "PDFs you saved stay where they are." "Rentals that had it keep its name."
- No exclamation marks, no emoji in the UI.

---

## 8. Layout of the main window

**The glass** (`ui/components/glass.py`), after Apple's Liquid Glass (iOS 26/27, macOS 26+): the window is a flat,
quiet backdrop (`WINDOW_TOP`, a step darker than the panels, so the accent's group rows stand out on it), the content sits on it, and the tools float above it on rounded, see-through
panels (`GLASS`, `GLASS_EDGE`, `GLASS_R`, a painted shadow). Search, dropdowns and buttons are capsules; the
+ and export buttons are circles; "add" buttons are tinted capsules (`widgets.add_chip`). Table rows highlight
as one rounded shape across the row (`tables.RowPainter`); a divider under the mouse goes a step brighter
(`DIVIDER_HOVER`), never white or black. Qt can't blur what's behind a widget, so the glass is a tint, not a blur.

**The inspector only shows with something picked** (or the assistant open). It slides in (`Dock`, `DOCK_MS`) when
you click a row and slides out on Esc, a click on empty space or its ✕. The search capsule is centred in the toolbar.

```
╭ bodega. ──────────╮  All Gear 18   (⌕ Search                ) (≡)    (⇪) (☺) (+)  ╭ Gear          (⋯)(✕) ╮
│ Inventory ˅    (+)│  Name                       Company   Qty  Status  With Tax  Rate │ Out · Northwind · Oct 25 │
│ ▸ All Gear      18│  ▾ Body                               4           $6,992  $280│ photo                    │
│ ▾ Kits           1│  ⋮ Sony FX6 Cinema Camera  +3 Sony     1  In       $6,493  $260│ Sony FX6 Cinema Camera   │
│     FX6 Run & Gun │  ⋮ Tilta Cage …  with Sony FX6 Tilta   1  In         $302   $12│ ╭ Details ────────────╮  │
│ Rentals ˅      (+)│  …                                                             │ ╭ Value & Rate ───────╮  │
│ ▸ All Rentals    1│                                                                │ + Photo  + Link  + Notes │
│   Calendar        │                                                                │                          │
│ ╭ JL Juniper Lane ⇕╮│  Pieces 38   Paid $21,223   Tax $1,751   With Tax $22,974     │ [     Rent This…       ] │
╰───────────────────╯                                                                  ╰──────────────────────────╯
```
Full screen, three columns: **where you are → a big table of it → the one you picked, editable.** Inventory first;
rentals are the plus underneath.

- **The sidebar is where you are** (`ui/sidebar.py`, `SIDEBAR_W`): All Gear, one row per group, Kits; then Out
  Now, Coming Up, All Rentals, Calendar. Groups are the one way gear is organised (no departments on screen;
  a sheet's departments are only read while importing). Tidy Up Groups (`core/tidy.py`) gives them plain names. Each with a count; Out Now turns red when something's late.
- **The middle is one table** (`ui/tables.py`): a toolbar (`TOOLBAR_H`) with the place's name and count, Search,
  the filter icon (`filters.FilterButton`: Divide By, Show, Company, Missing, Clear Filters; the accent while on),
  the share button (import, Google Sheets, inventory list, rate card, labels, CSV), the assistant, then **one
  primary round +**: New Gear or New Group / New Kit / New Rental. Columns sort by clicking their header.
  The Calendar (`ui/calendar_view.py`) replaces the table for rentals: one row per rental, a bar per stretch of dates.
- **Gear is divided** by group in All Gear and by company inside a group (or not at all): an accent band (`DIVIDER`,
  painted by `tables._DividerBand`; the stylesheet ignores a row's own background) with its name and totals in
  `DIVIDER_TEXT`, click to fold it (remembered). Columns follow a gear sheet: Qty, Status, Paid, With Tax, Day Rate.
- **Categories are yours.** Department and Group are picked from a list (with New Department… / New Group…
  at the bottom). Right-click a divider or a department in the sidebar to rename, move up or down, move a group
  to another department, or remove it; + beside Inventory makes a department. Pick several rows (Shift or
  Cmd-click) and Move To…, or drag them onto a divider or a department in the sidebar. Attached gear comes along.
- **Picking many.** Cmd+A picks everything showing (not hidden or folded rows); Shift and Cmd-click work too. Delete
  (or Backspace) deletes them after a warning that names them and counts the attached gear that goes with them.
- **Every piece has its own row.** Gear that goes with another piece says so in grey after its name ("with Sony
  FX6"); the piece shows "+3". Each row's numbers are that piece alone, so the dividers and the totals add up.
- **Moves wait for the drag to end** (`GearTable.after_drag`): refilling the table mid-drag blanked it on the Mac.
- **Money fields read as money** (`widgets.MoneyField`): "$5,998.00" until clicked, then the plain number.
- **A totals bar under the gear table**: pieces, paid, tax, with tax, day rate, for what's showing.
- **The right is the one you picked, and it's where you change it** (`INSPECTOR_W`). Header: the title and ⋯
  (Duplicate, Delete…). Footer: the one main action, full width (Rent This…, Kit Sheet…, Agreement…). The header
  is `TOOLBAR_H` tall so its line meets the toolbar's. Nothing picked and nothing in the table: it hides.
- **Gear shows only what it has.** Name, Company, Series, Department, Group, How Many, Status, Value & Rate are
  always there; Link, Serial Numbers, Works With and Notes appear when they hold something or you add them
  (+ Add). An empty added part has an × to take it off. Works With replaces attaching + Belongs To: the gear
  that goes with a piece (or the piece it goes with), each a row that opens it; Add… picks more.
- **The gear table's columns are yours**: right-click the column titles to show or hide them (Series and Paid
  start hidden). The grip column (dots, painted by `tables._GearPainter`) is your order: drag rows by it.
  Click a column title to sort by it; click the grip column's to go back to your order. On a smaller window
  columns step aside (`GIVE_WAY`) so Name keeps `NAME_MIN`, the inspector narrows to `INSPECTOR_MIN`, and the
  search box shrinks to `SEARCH_MIN`: nothing in the toolbar ever touches or overlaps. Divide by department,
  group, company or nothing (toolbar).
- **Pages open in their own window** (`preview.PageDialog`): the agreement, kit sheet, inventory list and rate card,
  with Save PDF…, Print… and ⋯. They're never in the way while you edit.
- **No overview, no repeats.** What a piece's overview used to say lives where it's used: the "Booked · … · dates"
  line at the top of the gear panel, the Status column, the calendar.
- **Nothing to save by hand.** Edits save `SAVE_DELAY_MS` after typing stops, on switching, and on quit.
- **Every group in a panel is a Card**; in kits and rentals they fold away (`widgets.Disclosure`), remembered per
  panel, and say what's inside when folded.
- **Rental lines fold to one row each** (name, amount, ⋯), one open at a time. A line with its own dates shows a
  small accent calendar; a line with gear that isn't free shows a red alert and says why when opened.
- **Adding gear goes through one window** (`gear_picker.GearPicker`): search, tick, Add. The same window attaches
  gear to a piece, fills a package and puts gear on a rental.
- **Only show what applies**: Open beside Belongs To only when it belongs to something; Attach Gear… only on a
  top-level piece; the Discount or Day Rate field only for that pricing; dates on a line only with Its Own Dates.
- **Removing goes through a menu or a confirmation, never a single click.**
- **Menus hold commands, the panels hold settings.** File / Edit / View / Profile / AI / Window / Help in the Mac
  menu bar; the profile card at the bottom of the sidebar opens profiles, Send Feedback and Settings on every system.
- **Scrolling never changes a value**, and menus open on click, never on hover (`app._RoundPopups`).
- **One identity everywhere.** The icon is "b." on the family's dark tile, the full stop in the accent
  (`scripts/make_icon.py`); in the app the wordmark is "bodega." with the same blue full stop; on the Mac the title bar is ours (`ui/titlebar.py`).

---

## 9. The paper

Every page is laid out once in `doc/render.py` and painted on any device, so preview, PDF, PNG and print match.

- Sizes are in **points** (Letter 612 × 792), `MARGIN` 44 all round, a footer on every page ("Page N of M").
- Reading order, every page: who it's from (logo, name, tagline, contact) and **the one number that matters** on
  the right, in the accent (Total / Replacement Value / Day Rate) → the strip (four facts) → the blocks (Renter /
  Owner / Production) → the table → the totals → the note → the terms → signatures.
- Small labels are capitals with letter-spacing (`LABEL_SPACING`); everything else is sentence case.
- Ink, soft ink, faint ink and rules come from `core/looks.palette()`; the Dark Page swaps the whole palette
  (preview only). The accent shows on the big number, the Total line and group labels.
- Attached gear sits under its piece, indented with a small elbow, in soft ink, "Included" instead of a price.
- A rental whose lines have different dates is grouped by date range (accent subheadings), fees last, so what goes
  out together is checked out together. Out / In boxes sit in front of every piece on an agreement (not a quote).
- Serial numbers are IBM Plex Mono, small and faint, under the name ("S/N 5021734").
- Terms print as a two-column list: each clause's first words (up to the first ". ") bold on the left.
- Headings stay with the row under them; table headers repeat on new pages; totals and signatures stay together.
- Exports are written to a temp file beside the target and moved into place when complete.

---

## 10. Checklist before you commit a UI change

1. No raw numbers or colors outside `tokens.py`. This should print nothing:
   `grep -nE '[^{_A-Z0-9][0-9]{2,}px|#[0-9A-Fa-f]{6}|rgba' bodega/ui/*.py | grep -v tokens.py`
   (1px hairline borders are the one allowed literal.)
2. New controls are `CONTROL_H` tall (or `SMALL_H` for icon buttons) and line up with their neighbours.
3. Every icon-only button has a tooltip.
4. Labels are short and in Title Case; sentences (tooltips, hints, messages) are plain sentences.
5. Screenshots look right: `QT_QPA_PLATFORM=offscreen python tests/screenshot.py OUTDIR`.
