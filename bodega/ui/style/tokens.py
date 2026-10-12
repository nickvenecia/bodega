"""Design tokens (the same system as Listo): the ONLY place sizes, spacing, type and colors are defined.

Every widget, layout and stylesheet rule uses these names. If something needs a value
that isn't here, add a token (and document it in DESIGN.md) instead of typing a number.
"""

from __future__ import annotations

# ---------------------------------------------------------------- spacing (4-pt grid)
SPACE_1 = 4  # tight: a label and its control, an icon and its text
SPACE_2 = 8  # related items: buttons in a row, cards in the list, options in a stack
SPACE_3 = 12  # between groups (sections) inside a panel
SPACE_4 = 16  # padding of panels, bars and the main areas
SPACE_5 = 24  # padding of dialogs and the empty-state drop zone

# ---------------------------------------------------------------- control sizes
CONTROL_H = 34  # EVERY button, dropdown, text field and segmented control
SMALL_H = 24  # chips, token buttons, icon-only buttons
INDICATOR = 16  # standard icon size
TOGGLE_ROW_H = 32  # an on/off setting: label left, switch right
TOGGLE_W, TOGGLE_H = 36, 20  # the switch
TOGGLE_INSET = 3  # gap between the switch's track and its knob
ICON = 16
ICON_SM = 14
ICON_LG = 20  # the assistant's bubble in its toolbar button (sized to fill the circle)
BAR_H = 6  # progress bars
TRACK_H = 4  # slider groove
HANDLE = 14  # slider handle
SCROLL_W = 10  # scrollbar width
SCROLL_GUTTER = SCROLL_W  # space always kept for it (see widgets.FitScroll)
SCROLL_MIN = 30  # shortest scrollbar handle

# ---------------------------------------------------------------- corner radius
RADIUS_XS = 4  # checkbox box
RADIUS_SM = 6  # chips, menu/list rows, small buttons
RADIUS = 8  # controls: buttons, fields, dropdowns, segmented controls
RADIUS_LG = 12  # cards, popups, panels inside dialogs

# ---------------------------------------------------------------- type scale (px)
TEXT_XS = 11  # chips
TEXT_SM = 12  # secondary text: file details, hints, tooltips
TEXT_MD = 13  # body text and every control (the default)
TEXT_LG = 14  # emphasized text: file names in the list, footer title
TEXT_XL = 18  # dialog titles, empty-state headline
TEXT_TITLE = 24  # the page's large title (All Gear, Lights)
TEXT_BRAND = 21  # the "bodega." wordmark only
TEXT_TITLEBAR = 15  # the wordmark in the Mac title bar

WEIGHT_REGULAR = 400
WEIGHT_MEDIUM = 500  # controls
WEIGHT_SEMIBOLD = 600  # titles, labels, primary button
WEIGHT_BOLD = 700  # wordmark, dialog titles

# ---------------------------------------------------------------- layout
SIDEBAR_W = 232  # the sidebar: Inventory and Rentals
INSPECTOR_W = 420  # the panel on the right where the selected thing is edited
INSPECTOR_MIN = 360  # …on a smaller window
INSPECTOR_SHARE = 0.27  # of the window's width, between those two
HEADER_H = 52  # the numbered step header on top of every panel
TITLEBAR_H = 32  # Bodega's own Mac title bar (fitted to the real one once the window shows)
SEG_INSET = 2  # gap between a segmented control's frame and its buttons
ROW_INDENT = 18  # attached gear in the list, per level
TEXT_BOX_H = 2 * CONTROL_H - SPACE_2  # a two-line text box (addresses, notes)
MENU_ROW_H = CONTROL_H - SPACE_2  # a row in a menu, a dropdown's list or a picker
CHIP_SM_H = SMALL_H - 6  # the small status chip
SCROLL_INSET = 2  # a scrollbar's handle sits this far inside its track
TEXT_BOX_TALL = 4 * CONTROL_H - SPACE_3  # notes
TEXT_BOX_TERMS = 9 * CONTROL_H  # the agreement's terms
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
TABLE_ROW_H = 34  # one row in the gear, kit and rental tables
NAME_MIN = 240  # the gear table's Name column never gets narrower; other columns step aside
GRIP_W = 28  # the grip column you drag a gear row by
GRIP_GAP = 5  # between the grip's dots
CHEVRON = 9  # a divider's open/closed chevron
GLASS_R = 18  # a floating glass panel's corners
GLASS_GAP = 10  # between the window's edge and its floating panels, and between panels
GLASS_SHADOW_STEPS = 10  # layers of a panel's shadow
GLASS_SHADOW_SPREAD = 14  # how far it reaches
GLASS_SHADOW_DROP = 4  # how far below the panel it sits
DOCK_MS = 240  # the inspector sliding in or out
LIFT_STEP_MS = 16  # dragging a row: how often the other rows move (about 60 a second)
LIFT_EASE = 0.3  # …and how far towards their new place each step (smaller is slower)
LIFT_ROWS_SHOWN = 3  # rows drawn on the lifted card when several move
LIFT_SHADOW_STEPS = 6
GLASS_SHEEN_H = 140  # a panel's top sheen fades out over this many pixels
GLASS_EDGE_FADE = 60  # its bright inner edge fades over this many
GLASS_EDGE_REST = 0.35  # …to this much of its strength
QUIT_WAIT_MS = 1500  # how long quitting waits for a price or update check to finish
SAVE_DELAY_MS = 400  # save this long after the last keystroke
TABLE_DELAY_MS = 350  # refresh the table this long after an edit
UPDATE_CHECK_DELAY_MS = 8000  # the automatic update check waits this long after opening
TOAST_MS = 3500  # how long a toast stays up
TOAST_MAX_W = 520
NAV_GAP = 2  # between rows in the sidebar
ROW_INSET = 2  # a table row's rounded highlight sits this far inside the row
LINE_STROKE = 1.8  # drawn chevrons
ICON_STROKE = 2.0  # the icon set's line width
GRIP_DOT = 1.2  # the radius of a dot in the drag grip
NOTES_H = 220  # what's new, in the update window
DIALOG_W_WIDE = DIALOG_W + 2 * SPACE_5  # dialogs with a two-column form (renter, profile)
DIALOG_W_XWIDE = DIALOG_W + 6 * SPACE_5  # the update window
PAGE_DIALOG_INSET = 80  # the page window stays this far inside the main window
PAGE_DIALOG_MIN_H = 600
LOGO_THUMB_MAX_W = 160
DAY_W_MIN = 22  # one day on the calendar, at its narrowest
CAL_BAR_INSET = 7  # a rental's bar sits this far inside its calendar row
TRACK_BRAND = -0.5  # letter spacing (px): the wordmark
TRACK_TITLEBAR = -0.3
TRACK_TITLE = -0.4  # page titles
REVIEW_COL_W = (180, 64, 150, 0, 130)  # the AI Review window's columns (0: takes the room)
REVIEW_W = 900
# the tables' fixed column widths
COL_W = {
    "kids": 40, "company": 130, "series": 110, "group": 140, "qty": 48, "status": 88, "paid": 100,
    "with_tax": 104, "day": 88, "pieces": 90, "rate": 110, "value": 120, "rental": 140, "production": 200,
    "dates": 190, "rental_status": 100, "total": 120, "earned": 96,
}  # fmt: skip
ROW_R = 9  # a table row's rounded highlight
TABLE_THUMB = 24  # a piece's photo before its name in the gear list
PHOTO_H = 200  # the photo at the top of a piece's panel
LOG_COST_W = 90  # the cost box in a maintenance line
CHIP_H = 28  # a tinted capsule button
SORT_ARROW = 10  # the sort arrow in a column title
NAV_H = 30  # one row in the sidebar
NAV_INSET = SCROLL_GUTTER  # a sidebar row's gap from the glass edge (the scroll bar's room on the right)
NAV_R = GLASS_R - NAV_INSET  # its corners: concentric with the glass (the curves run parallel)
MENU_GAP = 6  # between a button and the menu it opens
AVATAR = 32  # your profile's initials, bottom of the sidebar
ASSISTANT_ICON = 28  # the assistant's face next to its title
ASSISTANT_ICON_BIG = 64  # and saying hi in an empty chat
PROFILE_CARD_H = 48
TOOLBAR_H = 64  # the bar above a table: title, search, New
SEARCH_W = 440  # the search box gets the room the dropdowns had
SEARCH_MIN = 160  # the search box at its narrowest
PAGE_DIALOG_SIZE = (1100, 1000)  # the agreement / inventory / rate card window
DAY_W = 36  # one day on the rentals calendar
CAL_ROW_H = 40  # one rental on the rentals calendar
CAL_WEEKS_AHEAD = 8
CAL_NAME_W = 220  # the rental names beside the calendar
CAL_HEAD_H = 44  # months and day numbers above it
MONTH_HEAD_H = 28  # the weekday names above the month
MONTH_DAY_H = 26  # a day's number, at the top of its square
MONTH_BAR_H = 20  # a rental across the days it's out
MONTH_BAR_GAP = 3
MONTH_CELL_MIN_H = 96

# ---------------------------------------------------------------- colors: a dark and a light set
# The app follows the system (or View → Appearance). Read colors as tokens.X when drawing, never copy them
# into a constant at import: use() swaps them.
DARK = {
    "BG": "#111016",  # window background
    "PANEL": "#18171E",  # sidebar, footer, dialogs
    "CARD": "#1E1D26",  # cards, fields
    "CARD_HOVER": "#25242F",
    "CARD_SELECTED": "#231E3A",  # a selected card (cool, so it reads as violet)
    "RAISED": "#2A2935",  # buttons, popups
    "RAISED_HOVER": "#33323F",
    "RAISED_PRESS": "#262531",
    "BORDER": "#2C2B37",
    "BORDER_STRONG": "#3A3947",
    "BORDER_HOVER": "#4C4A5C",
    "BORDER_CHECK": "#5A5870",  # unchecked checkbox outline
    "TEXT": "#F3F1F8",
    "MUTED": "#A6A3B8",  # secondary text
    "FAINT": "#716E86",  # hints, disabled, section labels
    "WELL": "#0C0B11",  # sunken areas: thumbnails, previews, logs
    "ACCENT": "#8069F7",  # Franklin Mountains dusk violet — selection, primary action, focus
    # (Listo's is marigold, Cobro's turquoise)
    "ACCENT_HOVER": "#9A86FF",
    "ACCENT_PRESS": "#6A52E8",
    "ON_ACCENT": "#FFFFFF",  # text/icons on violet
    "ACCENT_OFF": "#2A2541",  # disabled primary button
    "ACCENT_OFF_TEXT": "#6E6895",
    "ACCENT_TINT": "rgba(140, 120, 255, 0.14)",  # violet wash
    "ACCENT_EDGE": "rgba(150, 130, 255, 0.55)",
    "GOOD": "#4CC38A",
    "BAD": "#F0616D",
    "BAD_TINT": "#2A1A1D",  # danger button hover
    "BAD_EDGE": "#5A2A30",  # failed card border
    "WARN": "#E9B949",
    "PAPER": "#FFFFFF",  # the paper (and logo thumbnails) in the preview
    "SHADOW": "rgba(0, 0, 0, 0.55)",  # the paper's shadow on the dark preview
    "DIVIDER": "#26213D",  # a department or group divider in the gear table: a violet band
    "DIVIDER_TEXT": "#B3A4FF",  # its name and totals
    "DIVIDER_HOVER": "#2F294B",  # a divider under the mouse: the same violet, a step brighter
    "ROW_HOVER": "rgba(255, 255, 255, 0.05)",  # a table row under the mouse
    "WINDOW_TOP": "#121118",  # the window's backdrop: flat, a step darker than the panels
    "WINDOW_BOTTOM": "#121118",
    "GLASS_TOP": "rgba(72, 66, 100, 0.74)",  # a floating panel's sheen at the top…
    "GLASS": "rgba(38, 35, 52, 0.80)",  # …fading to this at the bottom (sidebar, inspector)
    "GLASS_STROKE": "rgba(255, 255, 255, 0.09)",  # its outline, so it reads as its own sheet
    "GLASS_EDGE": "rgba(255, 255, 255, 0.08)",  # the bright line just inside it (strongest along the top)
    "GLASS_SHADOW": "rgba(0, 0, 0, 0.60)",
    "CHIP": "rgba(150, 130, 255, 0.16)",  # a tinted capsule (+ Link, + Notes)
    "CHIP_HOVER": "rgba(150, 130, 255, 0.26)",
    "FIELD": "rgba(255, 255, 255, 0.07)",  # a text field or dropdown: lightly frosted
    "FIELD_BORDER": "rgba(255, 255, 255, 0.08)",
    "BLOCK": "rgba(255, 255, 255, 0.045)",  # a card inside a glass panel: a soft tint, no outline
}
LIGHT = {
    "BG": "#F5F4F9",
    "PANEL": "#EEEDF4",
    "CARD": "#FFFFFF",
    "CARD_HOVER": "#EFEDF7",
    "CARD_SELECTED": "#ECE8FD",
    "RAISED": "#FFFFFF",
    "RAISED_HOVER": "#F3F1F9",
    "RAISED_PRESS": "#E7E4F1",
    "BORDER": "#E3E0EE",
    "BORDER_STRONG": "#D4D0E3",
    "BORDER_HOVER": "#B6B0CC",
    "BORDER_CHECK": "#A19CB5",
    "TEXT": "#1C1A26",
    "MUTED": "#686480",
    "FAINT": "#9C98B0",
    "WELL": "#E6E3EF",
    "ACCENT": "#6A52E8",
    "ACCENT_HOVER": "#7A64F0",
    "ACCENT_PRESS": "#5840D4",
    "ON_ACCENT": "#FFFFFE",
    "ACCENT_OFF": "#DCD6F8",
    "ACCENT_OFF_TEXT": "#9A90D0",
    "ACCENT_TINT": "rgba(106, 82, 232, 0.09)",
    "ACCENT_EDGE": "rgba(106, 82, 232, 0.45)",
    "GOOD": "#1E9A5E",
    "BAD": "#D3374A",
    "BAD_TINT": "#FBEAEC",
    "BAD_EDGE": "#EFB7BF",
    "WARN": "#A97A06",
    "PAPER": "#FFFFFF",
    "SHADOW": "rgba(0, 0, 0, 0.16)",
    "DIVIDER": "#E0D9F8",
    "DIVIDER_TEXT": "#5840D4",
    "DIVIDER_HOVER": "#D3C9F7",
    "ROW_HOVER": "rgba(60, 40, 140, 0.05)",
    "WINDOW_TOP": "#EFEDF5",
    "WINDOW_BOTTOM": "#EFEDF5",
    "GLASS_TOP": "rgba(255, 255, 255, 0.94)",
    "GLASS": "rgba(255, 255, 255, 0.76)",
    "GLASS_STROKE": "rgba(40, 25, 100, 0.13)",
    "GLASS_EDGE": "rgba(255, 255, 255, 1.0)",
    "GLASS_SHADOW": "rgba(35, 20, 80, 0.16)",
    "CHIP": "rgba(106, 82, 232, 0.10)",
    "CHIP_HOVER": "rgba(106, 82, 232, 0.18)",
    "FIELD": "rgba(255, 255, 255, 0.92)",
    "FIELD_BORDER": "rgba(50, 30, 120, 0.12)",
    "BLOCK": "rgba(90, 70, 190, 0.05)",
}
SCHEME = "dark"
globals().update(DARK)


def use(scheme: str) -> None:
    """Switch every color token to the dark or light set."""
    global SCHEME
    SCHEME = "light" if scheme == "light" else "dark"
    globals().update(LIGHT if SCHEME == "light" else DARK)
