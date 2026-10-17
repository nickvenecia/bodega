"""Design tokens: the ONLY place sizes, spacing, type and colors are defined.

Every widget, layout and stylesheet rule uses these names. If something needs a value
that isn't here, add a token (and document it in DESIGN.md) instead of typing a number.
"""

from __future__ import annotations

from itertools import pairwise

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
HAIRLINE = 1  # a hairline between rows
GROUP_INSET = 16  # (G.12) grouped rows: the rows' leading inset in their card, where hairlines start
GROUP_GAP = 24  # (G.12) between groups of rows
CHOICE_ROW_H = 32  # (choice-row) menus, dropdown lists, pickers, the sidebar
SECTION_ADD = TARGET_MIN  # a sidebar section's plain + (a gray glyph; its row is a target too)
INDICATOR = 16  # (check) a checkbox
TOGGLE_ROW_H = ROW_H  # an on/off setting: label left, switch right
TOGGLE_W, TOGGLE_H = 44, 26  # (switch) its track; the knob is the height − 4
TOGGLE_INSET = 2  # gap between the switch's track and its knob
ICON = 15  # (icon-ctl) icons inside controls and fields
ICON_BAR = 18  # (icon-bar) icons in the bar
ICON_SM = 12  # a chevron, a small mark beside words
ICON_UPDOWN = 14  # a dropdown's up/down mark
ICON_LG = 20  # the assistant's bubble in its toolbar button (sized to fill the circle)
BAR_H = 6  # progress bars
TRACK_H = 4  # slider groove
HANDLE = 14  # slider handle
SCROLL_W = 10  # scrollbar width
SCROLL_GUTTER = SCROLL_W  # room kept for it beside the content (see widgets.FitScroll): none for bars that lie over
# the content (use(bars_over=True), the standard's I-09); the scroll bar's width where the system always shows them
SCROLL_HIDE_MS = 1000  # an overlay scroll bar is gone this long after scrolling stops
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
ROW_INDENT = 18  # (G.11) gear that goes with a piece, under it: its name this much further in
DISCLOSURE = 12  # (G.11) a piece's chevron, before its name, when gear goes with it…
DISCLOSURE_GAP = 6  # …this far before what follows it
TEXT_BOX_H = 2 * CONTROL_H - SPACE_2  # a two-line text box (addresses, notes)
SCROLL_INSET = 2  # a scrollbar's handle sits this far inside its track
TEXT_BOX_TALL = 4 * CONTROL_H - SPACE_3  # notes
TEXT_BOX_TERMS = 7 * ROW_H  # the agreement's terms
NUM_FIELD_W = 96  # qty / rate fields
ROW_CTL = 320  # (row-ctl) a field that holds a name, an email, a phone or a key, in a form with room
ROW_CTL_SHORT = 120  # (row-ctl-short) …one that holds a rate, a number, a prefix or a code
QTY_FIELD_W = 64  # a quantity on its own
LOGO_THUMB = 40  # the logo preview in the profile dialog
PAGE_GAP = 24  # space between preview pages
PAGE_SHADOW = 18  # blur of the paper's shadow in the preview
DIALOG_W = 480
SETTINGS_SIZE = (820, 620)  # the Settings window
SETTINGS_MIN = (680, 480)
SETTINGS_SIDE_W = 210  # its sidebar
ALERT_W = 300  # an alert (Delete …?), narrow like a Mac's
SHEET_PAD = (16, 48)  # (G.18) a sheet keeps this far from the window's sides, and from its top and foot
WINDOW_PAD = 28  # (G.18) …and the window over the app (Settings), this far all round
SHEET_BLUR = 6  # (G.18) the window behind a sheet, blurred this much…
WINDOW_BLUR = 10  # …behind Settings…
PALETTE_BLUR = 4  # …and behind Search Everything
SHEET_RISE = 10  # (G.18) a sheet rises this far as it comes in
SHEET_CLOSE_INSET = 18  # (G.18) a sheet's ✕: its trailing edge this far in from the sheet's
ALERT_ICON = 56  # the app icon at the top of it
PROFILE_DIALOG_H = 680  # the profile dialog: name, logo and contact show without scrolling
PICKER_SIZE = (560, 620)  # the Add Gear window
IMPORT_SIZE = (760, 800)  # the Import window
IMPORT_LIST_H = 320  # the list of pieces in the Import window
WINDOW_SIZE = (1600, 1000)
FILLED_SLACK = 4  # a window this close to the screen's size counts as filling it
TEXT_SLACK = 2  # room a label keeps past its words, so they never cut at the last pixel
WINDOW_MIN = (1280, 700)  # the toolbar, table and inspector all fit
NARROW_W = 1100  # a window narrower than this (a large text size on a small screen) folds its sidebar away (V-16)
TABLE_ROW_H = ROW_H  # one row in the gear, kit and rental tables
NAME_MIN = 240  # the gear table's Name column never gets narrower; other columns step aside
RENTER_MIN = 160  # the rentals table's Renter column, the same way
GRIP_W = 28  # the grip column you drag a gear row by (at the row's trailing edge, the standard's 4.18)
TICK_W = 36  # (G.10.3) the tick column every list leads with; its box is INDICATOR
LIST_CARD_INSET = (8, 4)  # (G.10.1) a page's list sits this far inside its card: across, then down
CHECK_STROKE = 1.75  # the tick mark's line inside a ticked box
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
SHEET_FADE_MS = 160  # (G.18) the scrim behind a sheet fades in…
SHEET_RISE_MS = 200  # …and the sheet rises into place
TURN_MS = 180  # (G.11) a chevron turning as what it holds opens or closes
LIFT_STEP_MS = 16  # dragging a row: how often the other rows move (about 60 a second)
LIFT_EASE = 0.3  # …and how far towards their new place each step (smaller is slower)
LIFT_ROWS_SHOWN = 3  # rows drawn on the lifted card when several move
LIFT_SHADOW_STEPS = 6
# (§6.2) hover's lift on the accent-filled controls: a touch larger over a soft shadow, at dur-hover
LIFT_SCALE = 0.04  # how much larger (a 28-point button grows about a point each side)
LIFT_MS = 120
LIFT_SHADOW_BLUR = 10
LIFT_SHADOW_DROP = 3
GLASS_EDGE_FADE = 60  # the hairline is brightest along the top, settling over this many px
QUIT_WAIT_MS = 1500  # how long quitting waits for a price or update check to finish
SAVE_DELAY_MS = 400  # save this long after the last keystroke
KEY_CHECK_MS = 700  # a typed API key is tried once it rests this long
SAVE_MAX_MS = 3000  # …and never longer than this after the first unsaved change
MIDNIGHT_SLACK_MS = 1000  # the new day's refresh runs just after midnight
SAVE_RETRY_MS = 20000  # after a save failed: try again this often while it lasts
GC_MS = 50  # Python's cycle collector is checked on the window's thread this often (app._MainThreadGC)
AI_ASK_ABOVE = 5  # an AI job that may ask this many questions or more says so first
SALDO_CHECK_MS = 300  # how long to wait for Saldo to answer "are you open?"
TABLE_DELAY_MS = 350  # refresh the table this long after an edit
UPDATE_CHECK_DELAY_MS = 1500  # the automatic update check, just after the window is up (every launch)
UPDATE_WAIT_MS = 1500  # a found update waits this long between looks while another window is open
TOAST_MS = 3500  # how long a toast stays up
TOAST_WARN_MS = 6000  # …a problem, longer (the standard's toast-warning)
TOAST_UNDO_MS = 7000  # …one with Undo (the standard's 6 to 8 s; longer while the pointer rests on it)
TOAST_MS_PER_CHAR = 60  # …or longer, for a long one: time to read it
TOAST_MAX_W = 520
TOAST_IN_MS = 220  # it rises and fades in…
TOAST_OUT_MS = 180  # …and fades away
TOAST_RISE = 10  # how far it rises as it comes in
TOAST_LIFT = SPACE_4  # its gap above the bottom of the page
SPINNER_SM = 16  # (G.27) the small spinner: a ring this wide…
SPINNER_RING_SM = 2  # …this thick
SPINNER_TURN_MS = 800  # a turn in this long…
SPINNER_TURN_SLOW_MS = 2400  # …or this, under Reduce Motion
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
TRACK_BRAND = -0.5  # letter spacing (px): the wordmark (a mark, not words)
TRACK_TITLEBAR = -0.3
# (the standard's 2.7 and A.4) Every other text's letter spacing, by its size: Apple's table for San Francisco (Inter
# has no optical sizes of its own), a little looser below 12, none at 12, tighter from 13 to 23, looser from 24 up.
TRACKING = ((10, 0.12), (11, 0.06), (12, 0.0), (13, -0.08), (17, -0.43), (22, -0.26), (26, 0.22), (28, 0.38), (34, 0.4))


def tracking(size: float) -> float:
    """The letter spacing (px) for text `size` px tall: the table's, in a straight line between its sizes."""
    if size <= TRACKING[0][0]:
        return TRACKING[0][1]
    for (s0, t0), (s1, t1) in pairwise(TRACKING):
        if size <= s1:
            return round(t0 + (t1 - t0) * (size - s0) / (s1 - s0), 3)
    return TRACKING[-1][1]


REVIEW_COL_W = (180, 64, 150, 0, 130)  # the AI Review window's columns (0: takes the room)
REVIEW_W = 900
# the tables' fixed column widths
COL_W = {
    "company": 130, "series": 110, "group": 140, "qty": 48, "status": 88, "paid": 100,
    "with_tax": 104, "day": 88, "pieces": 90, "rate": 110, "value": 120, "rental": 140, "production": 200,
    "dates": 190, "rental_status": 100, "total": 120, "earned": 96, "with": 170,
}  # fmt: skip
ROW_R = RADIUS_SM  # a table row's rounded highlight
TABLE_THUMB = 24  # a piece's photo before its name in the gear list
PHOTO_H = 200  # (kept for older callers)
PHOTO_HEAD = 88  # a record's photo, beside its name in the head (the standard's 4.5)
LOG_COST_W = 90  # the cost box in a maintenance line
CHIP_H = 28  # a tinted capsule button
FILTER_CHIP_H = 26  # (G.10.6) an active filter's capsule: padding 0 6 0 12, its ✕ 4 after the words
FILTER_CHIP_GAP = 6  # between the capsules (and after Clear All)
SORT_ARROW = 10  # the sort arrow in a column title
NAV_H = CHOICE_ROW_H  # one row in the sidebar
NAV_INSET = SCROLL_W  # a sidebar row's gap from the glass edge (a scroll bar's width)
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
# Search Everything (⌘K): the command palette (the standard's G.23)
PALETTE_W = 640  # (palette-w) as wide as this, inside the window…
PALETTE_TOP = 90  # …this far from its top
PALETTE_MAX_H = 540  # at most this tall…
PALETTE_MAX_SHARE = 0.62  # …and this much of the window
PALETTE_PAD_X = 22  # its search field's sides
PALETTE_HEAD_H = 28  # a group's heading row ("Go To", "Gear", "Commands")
PALETTE_ICON = 17  # a row's icon…
PALETTE_TEXT_X = SPACE_3 + PALETTE_ICON + SPACE_3  # …and where its words start
PALETTE_FIND_H = 30  # the search field: Title 2 words, no box
AVATAR = 32  # your profile's initials, bottom of the sidebar
ASSISTANT_ICON = 28  # the assistant's face next to its title
ASSISTANT_ICON_BIG = 64  # and saying hi in an empty chat
# the assistant's conversation (the standard's G.25)
ASSISTANT_FACE = 30  # the sparkle before anything is said
ICON_SUGGEST = 17  # a suggestion's icon
BUBBLE_MAX = 0.82  # your message's bubble is at most this much of the conversation's width
BUBBLE_R = 18  # its corners…
BUBBLE_TAIL_R = 4  # …but the one at its trailing foot
MSG_ACTION = 26  # Copy, Edit, Ask Again under a message: quiet circles…
MSG_ACTION_ICON = 14  # …with small icons
COPIED_MS = 1200  # Copy's ✓ stays this long
SHIMMER_MS = 1800  # "Thinking…": light passes across it this often
RIM_MS = 2400  # the message field's rim turns once in this long while it works
COMPOSER_MIN_H = 36  # the message field: a capsule at least this tall…
COMPOSER_TEXT_MIN = 28  # …its words 28…
COMPOSER_TEXT_MAX = 140  # …to 140 tall, growing with what's typed
SEND_D = 28  # Send (and Stop) inside it
SEND_ICON = 16
EMPTY_PAD = (56, 16, 60)  # (G.10.9) an empty list's block: top, sides, foot
PROFILE_CARD_H = 48
TOOLBAR_H = 64  # the bar above a table: title, search, New
PAGER_LIFT = 22  # the record pager floats this far above the panel's foot
SELBAR_LIFT = 18  # (G.10.7) the selection bar floats this far above the content's foot
FIGURE_GAP = 12  # (G.10.5) between the figure row's tiles…
FIGURE_BELOW = 18  # …and below the row
FIGURE_PAD = (16, 12, 16, 12)  # a tile's padding (left, top, right, bottom)
STRIP_ABOVE = 22  # (G.17) a record's figure strip, this far under its head…
STRIP_PAD = 28  # …each figure this far from the hairlines either side of it (the first: 0 at its leading edge)
STRIP_PAD_MIN = 12  # …narrowed to this in a narrow panel before a figure is left out
HEAD_BELOW = 24  # (G.17) a record's head (and its strip) to what's under it
CARD_SHADOW_BLUR = 2  # (shadow-card) a card's shadow: barely there, 1 below
CARD_SHADOW_DROP = 1
SELBAR_H = CONTROL_H + 12  # …a capsule this tall (padding 6 8 6 16, gap 10)
SELBAR_PAD = (16, 6, 8, 6)  # (left, top, right, bottom)
SELBAR_GAP = 10
SELBAR_ACTION_GAP = 4  # between its action capsules
PAGER_TEXT_W = 84  # …and its "12 / 38" is at least this wide
PAGER_SHADOW = 16  # the blur of its soft shadow (the glass shadow's color)
PAGE_INSET = 28  # (the large title's inset) a page's title, its list's words and its last button sit this far in
PAGE_MAX_W = 1880  # (page-max-w) on a very wide window the page stops this wide and sits centred
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
DAY_CELL_W = 40  # (day-cell) a day in a date field's month: 7 of them make it 280 wide…
DAY_CELL_H = 38  # …and this tall, with its CONTROL_H circle in the middle
DAY_LETTERS_H = 16  # the row of weekday letters above them
DATE_GLYPH_ROOM = 34  # a date field keeps this much on its right for the calendar glyph
MONTH_DAY_CIRCLE = MONTH_DAY_H - 2 * SPACE_0_5  # a day's number sits in this square, inside that row
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
    "DIVIDER": "#262628",  # a department or group divider in the gear table: a quiet band, a step up from its card
    "DIVIDER_TEXT": "#F5F5F7",  # its name and totals
    "DIVIDER_HOVER": "#2C2C2E",
    "ROW_HOVER": "rgba(255, 255, 255, 0.05)",  # (row-hover) a table row under the mouse
    "WINDOW_TOP": "#0E0E10",  # the window's backdrop (canvas)
    "WINDOW_BOTTOM": "#0E0E10",
    "GLASS": "rgba(30, 30, 32, 0.84)",  # (side-glass) a floating panel: the sidebar, the inspector
    "GLASS_STROKE": "rgba(255, 255, 255, 0.10)",  # (glass-stroke) its one hairline
    "GLASS_EDGE": "rgba(255, 255, 255, 0.14)",  # (glass-edge) a little brighter along the top
    "GLASS_SHADOW": "rgba(0, 0, 0, 0.45)",  # (shadow-glass) soft and wide
    "CARD_SHADOW": "rgba(255, 255, 255, 0.06)",  # (shadow-card) on the dark: a faint light edge, not a shadow
    "TOAST": "#48484A",  # (toast) a step lighter than the panels, so it stands out over anything
    "TOAST_TEXT": "#F5F5F7",
    "TOAST_EDGE": "rgba(255, 255, 255, 0.12)",
    "TOAST_SHADOW": "rgba(0, 0, 0, 0.60)",
    "TOAST_TRACK": "rgba(255, 255, 255, 0.18)",  # a job's progress track (and its spinner's) on the toast
    "TOAST_BUTTON": "rgba(255, 255, 255, 0.14)",  # a job's Stop, a capsule on the toast
    "SCRIM": "rgba(0, 0, 0, 0.50)",  # (scrim) the window, dimmed (and blurred) under a sheet, Settings or a palette
    "LIFT_SHADOW": "rgba(0, 0, 0, 0.50)",  # (hover's lift) under a lifted accent control
    "SHEET_SHADOW": "rgba(0, 0, 0, 0.60)",  # (shadow-lg) a sheet's and Settings' shadow…
    "SHEET_RING": "rgba(255, 255, 255, 0.10)",  # …and its hairline ring
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
    "CARD_SHADOW": "rgba(0, 0, 0, 0.05)",
    "TOAST": "#1C1C1E",  # (toast) dark on the light page: easy to spot
    "TOAST_TEXT": "#F5F5F7",
    "TOAST_EDGE": "rgba(255, 255, 255, 0.10)",
    "TOAST_SHADOW": "rgba(0, 0, 0, 0.30)",
    "TOAST_TRACK": "rgba(255, 255, 255, 0.18)",
    "TOAST_BUTTON": "rgba(255, 255, 255, 0.14)",
    "SCRIM": "rgba(0, 0, 0, 0.25)",
    "LIFT_SHADOW": "rgba(0, 0, 0, 0.16)",  # (hover's lift, as shadow-lifted)
    "SHEET_SHADOW": "rgba(0, 0, 0, 0.20)",
    "SHEET_RING": "rgba(0, 0, 0, 0.08)",
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


def _on_soft() -> None:
    """Words on the accent's wash (the sidebar's chosen place, a chip, a menu's chosen row, a key cap): the accent's
    words and the muted ones, each taken just far enough toward the main text's side to read at 4.5:1 on the wash over the glass
    (aimed at SOFT_RATIO: the glass shades itself a touch more than its color says)."""
    g = globals()
    wash = _solid(g["CHIP_HOVER"], _solid(g["GLASS"], g["BG"]))  # (the deepest wash words sit on: a chip, hovered)
    ink = "#000000" if SCHEME == "light" else "#FFFFFF"
    g.update(
        {
            f"SOFT_{k}": _toward(g[src], ink, wash, SOFT_RATIO)
            for k, src in (("TEXT", "ACCENT_TEXT"), ("MUTED", "MUTED"))
        }
    )
    g.update(SOFT_WARN=_toward(g["WARN"], ink, wash, SOFT_RATIO), SOFT_BAD=_toward(g["BAD"], ink, wash, SOFT_RATIO))


SOFT_RATIO = 4.8


SCHEME = "dark"
ACCENT_KEY = APP_ACCENT
globals().update(DARK)
_off()


def use(
    scheme: str, accent: str | None = None, contrast: bool = False, opaque: bool = False, bars_over: bool | None = None
) -> None:
    """Switch every color token to the dark or light set, in the chosen accent (None keeps the current one;
    an unknown or empty one means Bodega's own). `contrast` (Increase Contrast): secondary words take the
    main text's color, faint ones the secondary's, and every edge is strong. `opaque` (Reduce Transparency):
    the glass is solid. `bars_over`: scroll bars lie over the content, so no room is kept for them (None keeps
    it as it was)."""
    global SCHEME, ACCENT_KEY, SCROLL_GUTTER
    if bars_over is not None:
        SCROLL_GUTTER = 0 if bars_over else SCROLL_W
    SCHEME = "light" if scheme == "light" else "dark"
    if accent is not None:
        ACCENT_KEY = accent if accent in ACCENTS else APP_ACCENT
    look = LIGHT if SCHEME == "light" else DARK
    globals().update(look)
    if ACCENT_KEY != APP_ACCENT:
        _name, dark, light = ACCENTS[ACCENT_KEY]
        globals().update(accent_set(light if SCHEME == "light" else dark, SCHEME))
    if SCHEME == "light":  # its neutrals lean toward the accent (the dark look stays near neutral)
        accent = accent_of(ACCENT_KEY, "light")
        globals().update({k: tint(look[k], accent, share) for k, share in TINT.items()})
        # the accent as words still reads on the canvas it leaned (4.5:1, the standard's A.1)
        globals()["ACCENT_TEXT"] = _toward(globals()["ACCENT_TEXT"], "#000000", globals()["BG"])
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
    _on_soft()


# (V-26, the standard's 2.3) The light look's neutrals lean toward the accent you pick: each keeps its lightness and
# takes this share of the accent's hue and colorfulness (in OKLab), so a pink accent gives warm whites, purple a lilac,
# blue cool blue-whites. Quiet for cards and menus, more for the canvas, more again for the side panels, most for the
# greys that are mostly see-through (lines and fills). Words that mean something (good, late) and the paper never lean.
TINT = {
    **dict.fromkeys(("PANEL", "CARD", "RAISED", "FIELD", "BLOCK"), 0.025),  # cards, menus, sheets, fields
    **dict.fromkeys(("CARD_HOVER", "RAISED_HOVER", "RAISED_PRESS", "WELL", "DIVIDER", "DIVIDER_HOVER"), 0.04),
    **dict.fromkeys(("BG", "WINDOW_TOP", "WINDOW_BOTTOM"), 0.05),  # the canvas
    "GLASS": 0.08,  # the side panels
    **dict.fromkeys(("TEXT", "DIVIDER_TEXT"), 0.03),
    **dict.fromkeys(("MUTED", "FAINT", "BORDER_CHECK"), 0.06),  # the greys of words
    **dict.fromkeys(
        (
            "BORDER",
            "BORDER_STRONG",
            "BORDER_HOVER",
            "FIELD_BORDER",
            "GLASS_STROKE",
            "FILL",
            "FILL_2",
            "FILL_3",
            "ROW_HOVER",
        ),
        0.2,
    ),
}


def _lin(u: float) -> float:
    u /= 255
    return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4


def oklab(c: str) -> tuple[float, float, float]:
    """A #RRGGBB color as OKLab: (lightness, green–red, blue–yellow)."""
    r, g, b = (_lin(v) for v in _rgb(c))
    lms = (
        0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b,
        0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b,
        0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b,
    )
    l_, m_, s_ = (max(0.0, v) ** (1 / 3) for v in lms)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def _from_oklab(lab: tuple[float, float, float]) -> tuple[float, float, float]:
    """OKLab back to sRGB, 0 to 255 (outside that range when the color can't be shown)."""
    L, a, b = lab
    long_, mid, short = (
        (L + 0.3963377774 * a + 0.2158037573 * b) ** 3,
        (L - 0.1055613458 * a - 0.0638541728 * b) ** 3,
        (L - 0.0894841775 * a - 1.2914855480 * b) ** 3,
    )
    linear = (
        4.0767416621 * long_ - 3.3077115913 * mid + 0.2309699292 * short,
        -1.2684380046 * long_ + 2.6097574011 * mid - 0.3413193965 * short,
        -0.0041960863 * long_ - 0.7034186147 * mid + 1.7076147010 * short,
    )
    return tuple(
        255 * (12.92 * x if abs(x) <= 0.0031308 else (1.055 * abs(x) ** (1 / 2.4) - 0.055) * (1 if x > 0 else -1))
        for x in linear
    )  # type: ignore[return-value]


def tint(c: str, accent: str, share: float) -> str:
    """`c` leaning `share` of the way toward `accent`'s hue and colorfulness, its lightness (and any see-through)
    kept. A color too light to take the tint (white) gives up the least lightness that lets it show true."""
    alpha = None
    if c.startswith("rgba("):
        *rgb, alpha = (float(x) for x in c[5:-1].split(","))
        c = _hex(rgb)
    L, a, b = oklab(c)
    _l, aa, ab = oklab(accent)
    a, b = a + (aa - a) * share, b + (ab - b) * share
    out = _from_oklab((L, a, b))
    while L > 0 and not all(-0.5 <= v <= 255.5 for v in out):
        L -= 0.001
        out = _from_oklab((L, a, b))
    return _hex(out) if alpha is None else _rgba(_hex(out), alpha)


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


_on_soft()  # (the dark look's, until use() picks one)
