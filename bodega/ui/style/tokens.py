"""Design tokens: the ONLY place sizes, spacing, type and colors are defined.

Every widget, layout and stylesheet rule uses these names. If something needs a value
that isn't here, add a token (and document it in DESIGN.md) instead of typing a number.
"""

from __future__ import annotations

# Spacing (4-pt grid)
SPACE_1 = 4  # tight: a label and its control, an icon and its text
SPACE_2 = 8  # related items: buttons in a row, cards in the list, options in a stack
SPACE_3 = 12  # between groups (sections) inside a panel
SPACE_4 = 16  # padding of panels, bars and the main areas
SPACE_5 = 24  # padding of dialogs and the empty-state drop zone
SPACE_1_5 = 6  # Apple's half-steps, for small insets only: a menu's inset…
SPACE_2_5 = 10  # …a sidebar or menu row's padding
SPACE_0_5 = 2  # the hairline gaps: a key cap's top and bottom, a number under a name

# Control sizes (the standard's A.5, pointer)
CONTROL_H = 28  # (control-h) EVERY button, dropdown, text field, segmented control and icon circle
SMALL_H = 20  # (control-sm) chips, token buttons, small icon buttons
TARGET_MIN = 24  # a small target inside a row that's clickable too: never less (WCAG 2.5.8's 24-point circle)
STATUS_DOT = 7  # a status's dot, before its word in a table
FOCUS_RING = 2  # a painted focus ring's width (the standard: at least 2 points)
FOCUS_GAP = 2  # its gap outside what it rings
BAR_CTRL_H = 36  # (bar-h) the bar's circles and search field
ROW_H = 44  # (row-h) list rows and grouped rows: a table's rows, an on/off setting
CHOICE_ROW_H = 32  # (choice-row) menus, dropdown lists, pickers, the sidebar
SECTION_ADD = TARGET_MIN  # a sidebar section's plain + (a gray glyph; its row is a target too)
INDICATOR = 16  # (check) a checkbox
TOGGLE_ROW_H = ROW_H  # an on/off setting: label left, switch right
TOGGLE_W, TOGGLE_H = 44, 26  # (switch) its track; the knob is the height − 4
TOGGLE_INSET = 2  # gap between the switch's track and its knob
ICON = 15  # (icon-ctl) icons inside controls and fields
ICON_BAR = 18  # (icon-bar) icons in the bar
ICON_SM = 12  # a chevron, a small mark beside words
ICON_LG = 20  # the assistant's bubble in its toolbar button (sized to fill the circle)
BAR_H = 6  # progress bars
TRACK_H = 4  # slider groove
HANDLE = 14  # slider handle
SCROLL_W = 10  # scrollbar width
SCROLL_GUTTER = SCROLL_W  # space always kept for it (see widgets.FitScroll)
SCROLL_MIN = 30  # shortest scrollbar handle

MENU_MIN_W = 210  # (menu-min-w) a menu's narrowest; it grows to its longest row
MENU_ROWS = 8  # (menu-rows) rows a dropdown list shows before it scrolls
MONOGRAM = 38  # the profile card's initials circle

# Corner radius (the standard's scale)
RADIUS_XS = 4  # (radius-xs) a checkbox's box, a key cap
RADIUS_SM = 8  # (radius-sm) rows in a menu or list, focus outlines, small buttons
RADIUS = 10  # (radius-md) fields, wells, notes
RADIUS_LG = 14  # (radius-lg) cards, menus, dropdown lists, grouped cards
RADIUS_XL = 18  # (radius-xl) sheets, panels with grouped content

# Type: Apple's macOS text styles (A.4, pointer)
TEXT_LARGE_TITLE = 26  # Large Title: a page's title (All Gear, Lights), Bold
TEXT_TITLE1 = 22  # Title 1: a record's name, Bold
TEXT_TITLE2 = 17  # Title 2: dialog titles, an empty page's headline
TEXT_TITLE3 = 15  # Title 3: emphasized lines (a footer's title)
TEXT_HEADLINE = 13  # Headline (Bold)
TEXT_BODY = 13  # Body: every control and most words (the default)
TEXT_CALLOUT = 12  # Callout: secondary words, hints, tooltips
TEXT_SUBHEAD = 11  # Subheadline: chips, small labels
TEXT_FOOTNOTE = 10  # Footnote / Caption: the smallest words (never smaller)
# the older names, each one of the styles
TEXT_XS = TEXT_SUBHEAD
TEXT_SM = TEXT_CALLOUT
TEXT_MD = TEXT_BODY
TEXT_LG = TEXT_TITLE3
TEXT_XL = TEXT_TITLE2
TEXT_TITLE = TEXT_LARGE_TITLE
TEXT_RECORD = TEXT_TITLE1
TEXT_BRAND = 21  # the "bodega." wordmark only (a mark, not words)
TEXT_TITLEBAR = 15  # the wordmark in the Mac title bar

WEIGHT_REGULAR = 400
WEIGHT_MEDIUM = 500  # controls
WEIGHT_SEMIBOLD = 600  # titles, labels, primary button
WEIGHT_BOLD = 700  # wordmark, dialog titles

# Layout
SIDEBAR_W = 244  # (sidebar-w) the sidebar: Inventory and Rentals
INSPECTOR_W = 420  # the panel on the right where the selected thing is edited
INSPECTOR_MIN = 360  # …on a smaller window
INSPECTOR_SHARE = 0.27  # of the window's width, between those two
HEADER_H = 52  # the numbered step header on top of every panel
TITLEBAR_H = 32  # Bodega's own Mac title bar (fitted to the real one once the window shows)
SEG_INSET = 2  # gap between a segmented control's frame and its buttons
ROW_INDENT = 18  # attached gear in the list, per level
TEXT_BOX_H = 2 * CONTROL_H - SPACE_2  # a two-line text box (addresses, notes)
SCROLL_INSET = 2  # a scrollbar's handle sits this far inside its track
TEXT_BOX_TALL = 4 * CONTROL_H - SPACE_3  # notes
TEXT_BOX_TERMS = 7 * ROW_H  # the agreement's terms
NUM_FIELD_W = 96  # qty / rate fields
QTY_FIELD_W = 64  # a quantity on its own
LOGO_THUMB = 40  # the logo preview in the profile dialog
PAGE_GAP = 24  # space between preview pages
PAGE_SHADOW = 18  # blur of the paper's shadow in the preview
DIALOG_W = 480
SETTINGS_SIZE = (820, 620)  # the Settings window
SETTINGS_MIN = (680, 480)
SETTINGS_SIDE_W = 210  # its sidebar
ALERT_W = 300  # an alert (Delete …?), narrow like a Mac's
ALERT_ICON = 56  # the app icon at the top of it
PROFILE_DIALOG_H = 680  # the profile dialog: name, logo and contact show without scrolling
PICKER_SIZE = (560, 620)  # the Add Gear window
IMPORT_SIZE = (760, 800)  # the Import window
IMPORT_LIST_H = 320  # the list of pieces in the Import window
WINDOW_SIZE = (1600, 1000)
WINDOW_MIN = (1280, 700)  # the toolbar, table and inspector all fit
TABLE_ROW_H = ROW_H  # one row in the gear, kit and rental tables
NAME_MIN = 240  # the gear table's Name column never gets narrower; other columns step aside
RENTER_MIN = 160  # the rentals table's Renter column, the same way
GRIP_W = 28  # the grip column you drag a gear row by
GRIP_GAP = SPACE_1  # between the grip's dots
CHEVRON = 9  # a divider's open/closed chevron
GLASS_R = 20  # (radius-glass) a floating glass panel's corners
GLASS_GAP = 10  # between the window's edge and its floating panels, and between panels
GLASS_SHADOW_STEPS = 16  # layers of a panel's shadow (soft, like the Mac's)
GLASS_SHADOW_SPREAD = 24  # how far it reaches: wide and faint, never a dark smudge
GLASS_SHADOW_DROP = 3  # how far below the panel it sits: barely
DOCK_MS = 240  # the inspector sliding in or out
FADE_MS = 150  # small things appearing or going (a sidebar section's +): a quick fade, never a pop
SEG_SLIDE_MS = 200  # a segmented control's highlight sliding to the new choice
LIFT_STEP_MS = 16  # dragging a row: how often the other rows move (about 60 a second)
LIFT_EASE = 0.3  # …and how far towards their new place each step (smaller is slower)
LIFT_ROWS_SHOWN = 3  # rows drawn on the lifted card when several move
LIFT_SHADOW_STEPS = 6
GLASS_EDGE_FADE = 60  # the hairline is brightest along the top, settling over this many px
QUIT_WAIT_MS = 1500  # how long quitting waits for a price or update check to finish
SAVE_DELAY_MS = 400  # save this long after the last keystroke
SAVE_MAX_MS = 3000  # …and never longer than this after the first unsaved change
MIDNIGHT_SLACK_MS = 1000  # the new day's refresh runs just after midnight
SAVE_RETRY_MS = 20000  # after a save failed: try again this often while it lasts
AI_ASK_ABOVE = 5  # an AI job that may ask this many questions or more says so first
SALDO_CHECK_MS = 300  # how long to wait for Saldo to answer "are you open?"
TABLE_DELAY_MS = 350  # refresh the table this long after an edit
UPDATE_CHECK_DELAY_MS = 1500  # the automatic update check, just after the window is up (every launch)
UPDATE_WAIT_MS = 1500  # a found update waits this long between looks while another window is open
TOAST_MS = 3500  # how long a toast stays up
TOAST_WARN_MS = 6000  # …a problem, longer (the standard's toast-warning)
TOAST_MS_PER_CHAR = 60  # …or longer, for a long one: time to read it
TOAST_MAX_W = 520
TOAST_IN_MS = 220  # it rises and fades in…
TOAST_OUT_MS = 180  # …and fades away
TOAST_RISE = 10  # how far it rises as it comes in
TOAST_LIFT = SPACE_4  # its gap above the bottom of the page
NAV_GAP = 2  # between rows in the sidebar
ROW_INSET = 2  # a table row's rounded highlight sits this far inside the row
LINE_STROKE = 1.8  # drawn chevrons
ICON_STROKE = 2.0  # the icon set's line width
GRIP_DOT = 1.2  # the radius of a dot in the drag grip
NOTES_H = 320  # what's new, in the update window: as tall as its words, up to this (then it scrolls)
NOTES_LINE = 140  # what's new: the line height, in % of the font size
DIALOG_W_WIDE = DIALOG_W + 2 * SPACE_5  # dialogs with a two-column form (renter, profile)
DIALOG_W_XWIDE = DIALOG_W + 6 * SPACE_5  # the update window
PAGE_DIALOG_INSET = 80  # the page window stays this far inside the main window
PAGE_DIALOG_MIN_H = 600
LOGO_THUMB_MAX_W = 160
DAY_W_MIN = 22  # one day on the calendar, at its narrowest
CAL_BAR_INSET = SPACE_2  # a rental's bar sits this far inside its calendar row
TRACK_BRAND = -0.5  # letter spacing (px): the wordmark
TRACK_TITLEBAR = -0.3
TRACK_TITLE = 0  # page titles: the font's own spacing (nothing is tracked by hand but the wordmark)
REVIEW_COL_W = (180, 64, 150, 0, 130)  # the AI Review window's columns (0: takes the room)
REVIEW_W = 900
# the tables' fixed column widths
COL_W = {
    "kids": 40, "company": 130, "series": 110, "group": 140, "qty": 48, "status": 88, "paid": 100,
    "with_tax": 104, "day": 88, "pieces": 90, "rate": 110, "value": 120, "rental": 140, "production": 200,
    "dates": 190, "rental_status": 100, "total": 120, "earned": 96, "with": 170,
}  # fmt: skip
ROW_R = RADIUS_SM  # a table row's rounded highlight
TABLE_THUMB = 24  # a piece's photo before its name in the gear list
PHOTO_H = 200  # the photo at the top of a piece's panel
LOG_COST_W = 90  # the cost box in a maintenance line
CHIP_H = 28  # a tinted capsule button
SORT_ARROW = 10  # the sort arrow in a column title
NAV_H = CHOICE_ROW_H  # one row in the sidebar
NAV_INSET = SCROLL_GUTTER  # a sidebar row's gap from the glass edge (the scroll bar's room on the right)
NAV_R = GLASS_R - NAV_INSET  # its corners: concentric with the glass (the curves run parallel)
MENU_GAP = 6  # between a button and the menu it opens
# Every list of choices looks the same (the standard's G.7): menus, dropdown lists, pickers, suggestions.
# Rows sit LIST_INSET inside a list whose corners are LIST_R, so their corners (LIST_ROW_R) run parallel to it.
# (The sidebar and Settings' sections are the same choice rows inside the glass: NAV_*.)
LIST_R = RADIUS_LG  # (radius-lg) a menu's corners
LIST_INSET = SPACE_1_5  # its inset
LIST_ROW_R = RADIUS_SM  # a row's corners: 14 − 6, concentric
LIST_ROW_H = CHOICE_ROW_H
LIST_GAP = 0
LIST_SEARCH_ABOVE = 12  # a list longer than this always has search
AVATAR = 32  # your profile's initials, bottom of the sidebar
ASSISTANT_ICON = 28  # the assistant's face next to its title
ASSISTANT_ICON_BIG = 64  # and saying hi in an empty chat
START_TILE_W = 184  # one way to start on an empty page (three fit beside the inspector on the smallest window)
START_BADGE = 40  # the circle behind a start tile's icon
PROFILE_CARD_H = 48
TOOLBAR_H = 64  # the bar above a table: title, search, New
PAGE_INSET = 28  # (the large title's inset) a page's title, its list's words and its last button sit this far in
SEARCH_W = 280  # (bar-search-w) the bar's search field…
SEARCH_MIN = 160  # the search box at its narrowest
PAGE_DIALOG_SIZE = (1100, 1000)  # the agreement / inventory / rate card window
DAY_W = 36  # one day on the rentals calendar
CAL_ROW_H = 40  # one rental on the rentals calendar
CAL_WEEKS_AHEAD = 8
CAL_NAME_W = 220  # the rental names beside the calendar
CAL_HEAD_H = 44  # months and day numbers above it
MONTH_HEAD_H = 28  # the weekday names above the month
MONTH_DAY_H = 28  # a day's number, at the top of its square (today's circle: control height)
MONTH_DAY_CIRCLE = MONTH_DAY_H - 2 * SPACE_0_5  # today's circle, inside that row
MONTH_BAR_H = 20  # a rental across the days it's out
MONTH_BAR_GAP = SPACE_1
MONTH_CELL_MIN_H = 96

# Colors: a dark and a light set
# The app follows the system (or View → Appearance). Read colors as tokens.X when drawing, never copy them
# into a constant at import: use() swaps them. A color drawn in code goes through theme.qcolor() (it reads the
# rgba() form too). Values are the standard's Appendix A (A.1 light, A.2 dark, A.3 meanings); the names in
# brackets are its roles. Words sit at 4.5:1 or more on what's under them; FAINT is for placeholders only.
DARK = {
    "BG": "#0E0E10",  # (canvas) the window, behind the table and the glass
    "PANEL": "#1C1C1E",  # (surface) dialogs, footers
    "CARD": "#1C1C1E",  # (surface) cards, fields
    "CARD_HOVER": "#232325",  # (surface-2)
    "CARD_SELECTED": "#273852",  # (accent-soft over surface) a selected card
    "RAISED": "#2C2C2E",  # (raised) buttons, menus, popups
    "RAISED_HOVER": "#3A3A3C",
    "RAISED_PRESS": "#262628",
    "BORDER": "rgba(84, 84, 88, 0.55)",  # (border) field and control edges
    "BORDER_STRONG": "rgba(84, 84, 88, 0.80)",  # (border-strong) the rule above totals; a switch that's off
    "BORDER_HOVER": "#6C6C70",
    "BORDER_CHECK": "#8E8E93",  # an unticked box's edge
    "TEXT": "#F5F5F7",  # (text)
    "MUTED": "#A1A1A6",  # (text-muted) secondary words: hints, counts, labels (7.5:1)
    "FAINT": "#7C7C80",  # (text-faint) placeholders and incidental words only
    "WELL": "#232325",  # (surface-2) sunken areas: thumbnails, previews, logs
    "ACCENT": "#4A90F7",  # Bodega's blue, lifted for dark: selection, focus, icons, links
    "ACCENT_HOVER": "#6BA4F8",  # (accent-hover) mixed 18% toward white
    "ACCENT_PRESS": "#3D76CB",
    "ACCENT_FILL": "#3D76CB",  # under words (a primary button, +): white on it reads at 4.5:1
    "ACCENT_FILL_HOVER": "#4880D2",
    "ACCENT_TEXT": "#9CC2FB",  # (accent-text) the accent as words: mixed 45% toward white
    "ON_ACCENT": "#FFFFFF",  # (on-accent) words and icons on the accent fill
    "KNOB": "#FFFFFF",  # a switch's knob, on or off (Apple's)
    "ACCENT_TINT": "rgba(74, 144, 247, 0.24)",  # (accent-soft) a selection's wash
    "ACCENT_EDGE": "rgba(74, 144, 247, 0.45)",  # (accent-edge) an "on" control's edge
    "GOOD": "#30D158",  # success as words
    "GOOD_FILL": "#30D158",  # …as a fill (a switch that's on)
    "GOOD_SOFT": "rgba(48, 209, 88, 0.18)",
    "BAD": "#FF6B7E",  # danger as words: late, failed, delete
    "BAD_FILL": "#FF4245",
    "BAD_BUTTON": "#DB393B",  # a red button's fill: white words on it at 4.5:1
    "BAD_TINT": "rgba(255, 66, 69, 0.18)",  # (danger soft) a danger button's hover
    "BAD_EDGE": "rgba(255, 107, 126, 0.45)",
    "WARN": "#FFB340",  # warning as words
    "WARN_FILL": "#FF9230",
    "WARN_SOFT": "rgba(255, 146, 48, 0.18)",
    "INFO": "#5AB0FF",  # info as words: Booked (never the accent, which is for what you can press)
    "INFO_FILL": "#0091FF",
    "INFO_SOFT": "rgba(0, 145, 255, 0.18)",
    "INFO_EDGE": "rgba(90, 176, 255, 0.45)",
    "PAPER": "#FFFFFF",  # the paper (and logo thumbnails) in the preview
    "SHADOW": "rgba(0, 0, 0, 0.55)",  # the paper's shadow on the dark preview
    "DIVIDER": "#1C1C1E",  # a department or group divider in the gear table: a quiet band (it can't be pressed)
    "DIVIDER_TEXT": "#F5F5F7",  # its name and totals
    "DIVIDER_HOVER": "#232325",
    "ROW_HOVER": "rgba(255, 255, 255, 0.05)",  # (row-hover) a table row under the mouse
    "WINDOW_TOP": "#0E0E10",  # the window's backdrop (canvas)
    "WINDOW_BOTTOM": "#0E0E10",
    "GLASS": "rgba(30, 30, 32, 0.84)",  # (side-glass) a floating panel: the sidebar, the inspector
    "GLASS_STROKE": "rgba(255, 255, 255, 0.10)",  # (glass-stroke) its one hairline
    "GLASS_EDGE": "rgba(255, 255, 255, 0.14)",  # (glass-edge) a little brighter along the top
    "GLASS_SHADOW": "rgba(0, 0, 0, 0.45)",  # (shadow-glass) soft and wide
    "TOAST": "#48484A",  # (toast) a step lighter than the panels, so it stands out over anything
    "TOAST_TEXT": "#F5F5F7",
    "TOAST_EDGE": "rgba(255, 255, 255, 0.12)",
    "TOAST_SHADOW": "rgba(0, 0, 0, 0.60)",
    "TOAST_DONE": "#30D158",  # its icon: it worked
    "TOAST_PROBLEM": "#FFB340",  # …it didn't (amber: red means late or delete)
    "TOAST_PROBLEM_FILL": "#4A3F25",  # a problem's toast is tinted amber, so it's never missed
    "TOAST_PROBLEM_EDGE": "rgba(255, 179, 64, 0.45)",
    "BANNER": "rgba(255, 146, 48, 0.18)",  # (warning soft) a problem that lasts, across the top
    "BANNER_EDGE": "rgba(255, 179, 64, 0.45)",
    "CHIP": "rgba(74, 144, 247, 0.24)",  # (accent-soft) a tinted capsule button (+ Link, + Notes)
    "CHIP_HOVER": "rgba(74, 144, 247, 0.34)",  # (accent-soft-2)
    "FIELD": "rgba(255, 255, 255, 0.05)",  # (field) a text field or dropdown
    "FIELD_BORDER": "rgba(255, 255, 255, 0.12)",  # (field-border)
    "BLOCK": "rgba(255, 255, 255, 0.045)",  # a card inside a glass panel: a soft tint, no outline
    "FILL": "rgba(120, 120, 128, 0.24)",  # (fill) controls: a button, a field, a segmented track
    "FILL_2": "rgba(120, 120, 128, 0.16)",  # (fill-2) soft hovers and wells
    "FILL_3": "rgba(120, 120, 128, 0.34)",  # (fill-3) a filled control's hover; a switch that's off
    "BAD_HOVER": "rgba(255, 66, 69, 0.20)",  # a destructive button's hover
    "MONOGRAM_TOP": "#8E8E93",  # the profile card's grey gradient
    "MONOGRAM_BOTTOM": "#636366",
}
LIGHT = {
    "BG": "#F7F7F8",  # (canvas)
    "PANEL": "#FFFFFF",  # (surface)
    "CARD": "#FFFFFF",
    "CARD_HOVER": "#F2F2F4",  # (surface-2)
    "CARD_SELECTED": "#E8EFFB",
    "RAISED": "#FFFFFF",  # (raised)
    "RAISED_HOVER": "#F2F2F4",
    "RAISED_PRESS": "#E8E8EC",
    "BORDER": "rgba(60, 60, 67, 0.18)",
    "BORDER_STRONG": "rgba(60, 60, 67, 0.29)",
    "BORDER_HOVER": "rgba(60, 60, 67, 0.40)",
    "BORDER_CHECK": "#8A8A8E",
    "TEXT": "#1D1D1F",  # 15.7:1
    "MUTED": "#6A6A6F",  # 5.0:1 on the page, 4.6:1 on the glass (the standard's #6E6E73 is 4.3:1 there)
    "FAINT": "#8A8A8E",  # placeholders only
    "WELL": "#F2F2F4",
    "ACCENT": "#2F6FDB",
    "ACCENT_HOVER": "#285EBA",  # (accent-hover) mixed 15% toward black
    "ACCENT_PRESS": "#2453A6",
    "ACCENT_FILL": "#2F6FDB",  # white on it: 4.75:1
    "ACCENT_FILL_HOVER": "#285EBA",
    "ACCENT_TEXT": "#2B66CA",  # the accent as words on the canvas, at 4.5:1 or more
    "ON_ACCENT": "#FFFFFE",
    "KNOB": "#FFFFFF",  # a switch's knob, on or off (Apple's)
    "ACCENT_TINT": "rgba(47, 111, 219, 0.11)",
    "ACCENT_EDGE": "rgba(47, 111, 219, 0.45)",
    "GOOD": "#1F7A35",
    "GOOD_FILL": "#34C759",
    "GOOD_SOFT": "rgba(52, 199, 89, 0.13)",
    "BAD": "#C8102E",
    "BAD_FILL": "#FF383C",
    "BAD_BUTTON": "#C8102E",
    "BAD_TINT": "rgba(255, 56, 60, 0.12)",
    "BAD_EDGE": "rgba(200, 16, 46, 0.35)",
    "WARN": "#A05A00",
    "WARN_FILL": "#FF8D28",
    "WARN_SOFT": "rgba(255, 141, 40, 0.14)",
    "INFO": "#0062CC",
    "INFO_FILL": "#0088FF",
    "INFO_SOFT": "rgba(0, 136, 255, 0.12)",
    "INFO_EDGE": "rgba(0, 98, 204, 0.35)",
    "PAPER": "#FFFFFF",
    "SHADOW": "rgba(0, 0, 0, 0.16)",
    "DIVIDER": "#EDEDF0",
    "DIVIDER_TEXT": "#1D1D1F",
    "DIVIDER_HOVER": "#E5E5E9",
    "ROW_HOVER": "rgba(120, 120, 128, 0.08)",
    "WINDOW_TOP": "#F7F7F8",
    "WINDOW_BOTTOM": "#F7F7F8",
    "GLASS": "rgba(236, 236, 239, 0.90)",  # (side-glass) side at 90%
    "GLASS_STROKE": "rgba(60, 60, 67, 0.10)",
    "GLASS_EDGE": "rgba(255, 255, 255, 0.75)",
    "GLASS_SHADOW": "rgba(0, 0, 0, 0.09)",
    "TOAST": "#1C1C1E",  # (toast) dark on the light page: easy to spot
    "TOAST_TEXT": "#F5F5F7",
    "TOAST_EDGE": "rgba(255, 255, 255, 0.10)",
    "TOAST_SHADOW": "rgba(0, 0, 0, 0.30)",
    "TOAST_DONE": "#30D158",  # (the dark look's: these sit on the dark toast)
    "TOAST_PROBLEM": "#FFB340",
    "TOAST_PROBLEM_FILL": "#4A3F25",
    "TOAST_PROBLEM_EDGE": "rgba(255, 179, 64, 0.45)",
    "BANNER": "rgba(255, 141, 40, 0.14)",
    "BANNER_EDGE": "rgba(160, 90, 0, 0.35)",
    "CHIP": "rgba(47, 111, 219, 0.11)",
    "CHIP_HOVER": "rgba(47, 111, 219, 0.18)",
    "FIELD": "#FFFFFF",
    "FIELD_BORDER": "rgba(60, 60, 67, 0.22)",
    "BLOCK": "rgba(255, 255, 255, 0.85)",  # white cards on the grey glass
    "FILL": "rgba(120, 120, 128, 0.12)",
    "FILL_2": "rgba(120, 120, 128, 0.08)",
    "FILL_3": "rgba(120, 120, 128, 0.20)",
    "BAD_HOVER": "rgba(255, 56, 60, 0.20)",
    "MONOGRAM_TOP": "#A1A1A6",
    "MONOGRAM_BOTTOM": "#7C7C80",
}
# The accent you pick (Settings › General)
# Bodega's own is blue, hand-set in DARK / LIGHT above. The others are built from one color by accent_set().
# Never red: red means late, failed or delete.
APP_ACCENT = "blue"
ACCENTS = {  # key -> (name, on dark, on light)
    "blue": ("Blue", "#4A90F7", "#2F6FDB"),
    "purple": ("Purple", "#8069F7", "#6A52E8"),
    "pink": ("Pink", "#F25FA6", "#C9387F"),
    "orange": ("Orange", "#F5893A", "#C2600E"),
    "yellow": ("Yellow", "#EDBA3A", "#9C7104"),
    "green": ("Green", "#3DBE6E", "#1B8747"),
    "turquoise": ("Turquoise", "#2EBFB0", "#0D8178"),
    "graphite": ("Graphite", "#9B999F", "#68666D"),
}
SWATCH = 28  # a color circle in Settings
SWATCH_RING = 2  # the ring around the chosen one (and the gap inside it)
DARK_ON_ACCENT = "#141314"  # words on a light accent (yellow, green…), where white wouldn't read


def _rgb(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02X}" for v in rgb)


def _mix(c: str, into: str, amount: float) -> str:
    """`amount` of color c mixed into `into`."""
    a, b = _rgb(c), _rgb(into)
    return _hex(x * amount + y * (1 - amount) for x, y in zip(a, b, strict=True))


def _rgba(c: str, alpha: float) -> str:
    r, g, b = _rgb(c)
    return f"rgba({r}, {g}, {b}, {alpha:g})"


def luminance(c: str) -> float:
    """Relative luminance (WCAG), 0 black … 1 white."""

    def ch(v: int) -> float:
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = _rgb(c)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _toward(c: str, to: str, bg: str, ratio: float = 4.5) -> str:
    """`c` mixed toward `to` (black or white) just enough to read at `ratio` against `bg`."""
    step = 0.0
    out = c
    while contrast(out, bg) < ratio and step < 1:
        step += 0.02
        out = _mix(to, c, step)
    return out


def accent_set(base: str, scheme: str) -> dict[str, str]:
    """Every accent token for one color, in the dark or light look (the same steps as the hand-set blue):
    white words on its fill and its words on the canvas read at 4.5:1 or more."""
    light = scheme == "light"
    canvas = LIGHT["BG"] if light else DARK["BG"]
    fill = _toward(base, "#000000", "#FFFFFF")
    on = "#FFFFFE" if light else "#FFFFFF"
    if light:
        return {
            "ACCENT": base,
            "ACCENT_HOVER": _mix("#000000", base, 0.15),
            "ACCENT_PRESS": _mix("#000000", base, 0.25),
            "ACCENT_FILL": fill,
            "ACCENT_FILL_HOVER": _mix("#000000", fill, 0.15),
            "ACCENT_TEXT": _toward(base, "#000000", canvas),
            "ON_ACCENT": on,
            "ACCENT_TINT": _rgba(base, 0.11),
            "ACCENT_EDGE": _rgba(base, 0.45),
            "CARD_SELECTED": _mix(base, "#FFFFFF", 0.11),
            "CHIP": _rgba(base, 0.11),
            "CHIP_HOVER": _rgba(base, 0.18),
        }
    return {
        "ACCENT": base,
        "ACCENT_HOVER": _mix("#FFFFFF", base, 0.18),
        "ACCENT_PRESS": fill,
        "ACCENT_FILL": fill,
        "ACCENT_FILL_HOVER": _mix("#FFFFFF", fill, 0.06),
        "ACCENT_TEXT": _toward(_mix("#FFFFFF", base, 0.45), "#FFFFFF", canvas),
        "ON_ACCENT": on,
        "ACCENT_TINT": _rgba(base, 0.24),
        "ACCENT_EDGE": _rgba(base, 0.45),
        "CARD_SELECTED": _mix(base, DARK["CARD"], 0.24),
        "CHIP": _rgba(base, 0.24),
        "CHIP_HOVER": _rgba(base, 0.34),
    }


DISABLED_ALPHA = 0.4  # anything that's off (a button, a field, a menu item, a switch): drawn at 40%


def faded(c: str, under: str | None = None) -> str:
    """`c` as something that's off: at DISABLED_ALPHA, over `under` (a card, by default)."""
    if c.startswith("rgba("):
        *rgb, alpha = (float(x) for x in c[5:-1].split(","))
        return f"rgba({int(rgb[0])}, {int(rgb[1])}, {int(rgb[2])}, {alpha * DISABLED_ALPHA:g})"
    return _mix(c, under or globals()["CARD"], DISABLED_ALPHA)


def _off() -> None:
    """The colors of things that are off, from the colors they have when on: one rule, everywhere."""
    globals().update(
        TEXT_OFF=faded(TEXT),  # noqa: F821 (set from the look just before)
        FILL_OFF=faded(FILL_2),  # noqa: F821
        ACCENT_OFF=faded(ACCENT_FILL),  # noqa: F821  a primary button that's off
        ACCENT_OFF_TEXT=faded(ON_ACCENT),  # noqa: F821
        GOOD_OFF=faded(GOOD_FILL),  # noqa: F821  a switch that's on, but off
        KNOB_OFF=faded(KNOB),  # noqa: F821
        TRACK_OFF=faded(FILL_3),  # noqa: F821
    )


SCHEME = "dark"
ACCENT_KEY = APP_ACCENT
globals().update(DARK)
_off()


def use(scheme: str, accent: str | None = None, contrast: bool = False, opaque: bool = False) -> None:
    """Switch every color token to the dark or light set, in the chosen accent (None keeps the current one;
    an unknown or empty one means Bodega's own). `contrast` (Increase Contrast): secondary words take the
    main text's color, faint ones the secondary's, and every edge is strong. `opaque` (Reduce Transparency):
    the glass is solid."""
    global SCHEME, ACCENT_KEY
    SCHEME = "light" if scheme == "light" else "dark"
    if accent is not None:
        ACCENT_KEY = accent if accent in ACCENTS else APP_ACCENT
    look = LIGHT if SCHEME == "light" else DARK
    globals().update(look)
    if ACCENT_KEY != APP_ACCENT:
        _name, dark, light = ACCENTS[ACCENT_KEY]
        globals().update(accent_set(light if SCHEME == "light" else dark, SCHEME))
    if contrast:
        strong = look["BORDER_STRONG"]
        globals().update(
            MUTED=_toward(look["MUTED"], "#000000" if SCHEME == "light" else "#FFFFFF", look["BG"], 7),
            FAINT=look["MUTED"],
            **{  # words that carry a meaning reach 7:1 too
                k: _toward(look[k], "#000000" if SCHEME == "light" else "#FFFFFF", look["BG"], 7)
                for k in ("GOOD", "BAD", "WARN", "INFO")
            },
            BORDER=strong,
            FIELD_BORDER=strong,
            GLASS_STROKE=strong,
        )
    if opaque:
        globals().update(GLASS=_solid(look["GLASS"], look["BG"]), TOAST=_solid(look["TOAST"], look["BG"]))
    _off()


def _solid(c: str, under: str) -> str:
    """An rgba() color as the solid color it makes over `under`."""
    if not c.startswith("rgba("):
        return c
    r, g, b, a = (float(x) for x in c[5:-1].split(","))
    return _mix(_hex((r, g, b)), under, a)


def accent_of(key: str, scheme: str | None = None) -> str:
    """A choice's color in the dark or light look (the current one by default)."""
    _name, dark, light = ACCENTS.get(key, ACCENTS[APP_ACCENT])
    return light if (scheme or SCHEME) == "light" else dark
