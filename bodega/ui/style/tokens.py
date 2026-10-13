"""Design tokens: the ONLY place sizes, spacing, type and colors are defined.

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
SECTION_ADD = 20  # a sidebar section's plain + (a gray glyph, the Mac's size)
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
GLASS_SHADOW_STEPS = 16  # layers of a panel's shadow (soft, like the Mac's)
GLASS_SHADOW_SPREAD = 24  # how far it reaches: wide and faint, never a dark smudge
GLASS_SHADOW_DROP = 3  # how far below the panel it sits: barely
DOCK_MS = 240  # the inspector sliding in or out
FADE_MS = 150  # small things appearing or going (a sidebar section's +): a quick fade, never a pop
LIFT_STEP_MS = 16  # dragging a row: how often the other rows move (about 60 a second)
LIFT_EASE = 0.3  # …and how far towards their new place each step (smaller is slower)
LIFT_ROWS_SHOWN = 3  # rows drawn on the lifted card when several move
LIFT_SHADOW_STEPS = 6
GLASS_EDGE_FADE = 60  # the hairline is brightest along the top, settling over this many px
QUIT_WAIT_MS = 1500  # how long quitting waits for a price or update check to finish
SAVE_DELAY_MS = 400  # save this long after the last keystroke
TABLE_DELAY_MS = 350  # refresh the table this long after an edit
UPDATE_CHECK_DELAY_MS = 1500  # the automatic update check, just after the window is up (every launch)
UPDATE_WAIT_MS = 1500  # a found update waits this long between looks while another window is open
TOAST_MS = 3500  # how long a toast stays up
TOAST_MS_PER_CHAR = 60  # …or longer, for a long one: time to read it
TOAST_MAX_W = 520
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
# ---- every list of choices looks like the sidebar and Settings: menus, dropdown lists, pickers, suggestions.
# Rows sit LIST_INSET inside a list whose corners are LIST_R, so their corners (LIST_ROW_R) run parallel to it.
LIST_R = GLASS_R
LIST_INSET = NAV_INSET
LIST_ROW_R = NAV_R
LIST_ROW_H = NAV_H
LIST_GAP = NAV_GAP
AVATAR = 32  # your profile's initials, bottom of the sidebar
ASSISTANT_ICON = 28  # the assistant's face next to its title
ASSISTANT_ICON_BIG = 64  # and saying hi in an empty chat
START_TILE_W = (
    184  # one way to start on an empty page (three fit beside the inspector on the smallest window)
)
START_BADGE = 40  # the circle behind a start tile's icon
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
    "BG": "#1E1E1E",  # window background: the Mac's dark charcoal, not black
    "PANEL": "#1E1E1E",  # dialogs, footers
    "CARD": "#1F1E20",  # cards, fields
    "CARD_HOVER": "#262527",
    "CARD_SELECTED": "#1C2333",  # a selected card (a hint of the accent)
    "RAISED": "#2B2A2C",  # buttons, popups
    "RAISED_HOVER": "#343335",
    "RAISED_PRESS": "#272628",
    "BORDER": "#2D2C2E",
    "BORDER_STRONG": "#3B3A3D",
    "BORDER_HOVER": "#4D4B4F",
    "BORDER_CHECK": "#5C5A5F",  # unchecked checkbox outline
    "TEXT": "#F4F2F1",
    "MUTED": "#A8A5A6",  # secondary text
    "FAINT": "#737072",  # hints, disabled, section labels
    "WELL": "#0C0B0C",  # sunken areas: thumbnails, previews, logs
    "ACCENT": "#4A90F7",  # sky blue — selection, primary action, focus
    "ACCENT_HOVER": "#66A3FF",
    "ACCENT_PRESS": "#3478E0",
    "ON_ACCENT": "#FFFFFF",  # text/icons on the accent
    "ACCENT_OFF": "#1F2A3D",  # disabled primary button
    "ACCENT_OFF_TEXT": "#5E7499",
    "ACCENT_TINT": "rgba(74, 144, 247, 0.15)",  # a blue wash
    "ACCENT_EDGE": "rgba(102, 163, 255, 0.55)",
    "GOOD": "#4CC38A",
    "BAD": "#F0616D",  # late, failed, delete
    "BAD_TINT": "#2A1A1D",  # danger button hover
    "BAD_EDGE": "#5A2A30",  # failed card border
    "WARN": "#E9B949",
    "PAPER": "#FFFFFF",  # the paper (and logo thumbnails) in the preview
    "SHADOW": "rgba(0, 0, 0, 0.55)",  # the paper's shadow on the dark preview
    "DIVIDER": "#252F3F",  # a department or group divider in the gear table: a blue band
    "DIVIDER_TEXT": "#9CC2FF",  # its name and totals
    "DIVIDER_HOVER": "#2A3646",  # a divider under the mouse: the same blue, a step brighter
    "ROW_HOVER": "rgba(255, 255, 255, 0.05)",  # a table row under the mouse
    "WINDOW_TOP": "#1E1E1E",  # the window's backdrop: flat, darker than the panels (as on the Mac)
    "WINDOW_BOTTOM": "#1E1E1E",
    "GLASS": "rgba(48, 47, 50, 0.92)",  # a floating panel (sidebar, inspector): one even tone, lighter than the page
    "GLASS_STROKE": "rgba(255, 255, 255, 0.10)",  # its one hairline: faintly lighter than the panel
    "GLASS_EDGE": "rgba(255, 255, 255, 0.18)",  # …a little brighter along the top, where light catches it
    "GLASS_SHADOW": "rgba(0, 0, 0, 0.35)",  # soft and wide
    "CHIP": "rgba(74, 144, 247, 0.16)",  # a tinted capsule (+ Link, + Notes)
    "CHIP_HOVER": "rgba(74, 144, 247, 0.26)",
    "FIELD": "rgba(255, 255, 255, 0.07)",  # a text field or dropdown: lightly frosted
    "FIELD_BORDER": "rgba(255, 255, 255, 0.08)",
    "BLOCK": "rgba(255, 255, 255, 0.045)",  # a card inside a glass panel: a soft tint, no outline
    "FILL": "rgba(255, 255, 255, 0.045)",  # a soft fill on the page: a switch's track, weekends, a placeholder
}
LIGHT = {
    "BG": "#FFFFFF",
    "PANEL": "#FFFFFF",
    "CARD": "#FFFFFF",
    "CARD_HOVER": "#F2F2F4",
    "CARD_SELECTED": "#E8F0FD",
    "RAISED": "#FFFFFF",
    "RAISED_HOVER": "#F5F5F7",
    "RAISED_PRESS": "#E8E8EC",
    "BORDER": "#E5E5EA",
    "BORDER_STRONG": "#D8D8DD",
    "BORDER_HOVER": "#B8B8BF",
    "BORDER_CHECK": "#A2A2AA",
    "TEXT": "#1D1D1F",
    "MUTED": "#6E6E73",
    "FAINT": "#A1A1A6",
    "WELL": "#EDEDF0",
    "ACCENT": "#2F6FDB",
    "ACCENT_HOVER": "#3D7DE8",
    "ACCENT_PRESS": "#245CC0",
    "ON_ACCENT": "#FFFFFE",
    "ACCENT_OFF": "#D3E0F7",
    "ACCENT_OFF_TEXT": "#8FA9D6",
    "ACCENT_TINT": "rgba(47, 111, 219, 0.09)",
    "ACCENT_EDGE": "rgba(47, 111, 219, 0.45)",
    "GOOD": "#1E9A5E",
    "BAD": "#D3374A",
    "BAD_TINT": "#FBEAEC",
    "BAD_EDGE": "#EFB7BF",
    "WARN": "#A97A06",
    "PAPER": "#FFFFFF",
    "SHADOW": "rgba(0, 0, 0, 0.16)",
    "DIVIDER": "#DCE7FA",
    "DIVIDER_TEXT": "#245CC0",
    "DIVIDER_HOVER": "#CDDDF7",
    "ROW_HOVER": "rgba(0, 0, 0, 0.04)",
    "WINDOW_TOP": "#FFFFFF",
    "WINDOW_BOTTOM": "#FFFFFF",
    "GLASS": "rgba(242, 242, 245, 0.94)",
    "GLASS_STROKE": "rgba(0, 0, 0, 0.06)",  # a very faint gray hairline
    "GLASS_EDGE": "rgba(0, 0, 0, 0.04)",  # (fainter still along the top)
    "GLASS_SHADOW": "rgba(0, 0, 0, 0.08)",  # soft and wide
    "CHIP": "rgba(47, 111, 219, 0.10)",
    "CHIP_HOVER": "rgba(47, 111, 219, 0.18)",
    "FIELD": "rgba(255, 255, 255, 1.0)",
    "FIELD_BORDER": "rgba(0, 0, 0, 0.10)",
    "BLOCK": "rgba(255, 255, 255, 0.85)",  # white cards on the gray glass
    "FILL": "rgba(0, 0, 0, 0.045)",  # light gray on white
}
# ---------------------------------------------------------------- the accent you pick (Settings › General)
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
SWATCH = 22  # a color circle in Settings
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


def accent_set(base: str, scheme: str) -> dict[str, str]:
    """Every accent token for one color, in the dark or light look (the same steps as the hand-set blue)."""
    light = scheme == "light"
    on = "#FFFFFF" if contrast("#FFFFFF", base) >= 3 else DARK_ON_ACCENT
    if light:
        return {
            "ACCENT": base,
            "ACCENT_HOVER": _mix(base, "#FFFFFF", 0.9),
            "ACCENT_PRESS": _mix(base, "#000000", 0.85),
            "ON_ACCENT": "#FFFFFE" if on == "#FFFFFF" else on,
            "ACCENT_OFF": _mix(base, "#FFFFFF", 0.2),
            "ACCENT_OFF_TEXT": _mix(base, "#FFFFFF", 0.5),
            "ACCENT_TINT": _rgba(base, 0.09),
            "ACCENT_EDGE": _rgba(base, 0.45),
            "CARD_SELECTED": _mix(base, "#FFFFFF", 0.1),
            "DIVIDER": _mix(base, "#FFFFFF", 0.15),
            "DIVIDER_TEXT": _mix(base, "#000000", 0.85),
            "DIVIDER_HOVER": _mix(base, "#FFFFFF", 0.22),
            "CHIP": _rgba(base, 0.10),
            "CHIP_HOVER": _rgba(base, 0.18),
        }
    return {
        "ACCENT": base,
        "ACCENT_HOVER": _mix(base, "#FFFFFF", 0.85),
        "ACCENT_PRESS": _mix(base, "#000000", 0.88),
        "ON_ACCENT": on,
        "ACCENT_OFF": _mix(base, DARK["CARD"], 0.18),
        "ACCENT_OFF_TEXT": _mix(base, DARK["CARD"], 0.45),
        "ACCENT_TINT": _rgba(base, 0.15),
        "ACCENT_EDGE": _rgba(_mix(base, "#FFFFFF", 0.85), 0.55),
        "CARD_SELECTED": _mix(base, DARK["CARD"], 0.12),
        "DIVIDER": _mix(base, DARK["BG"], 0.15),
        "DIVIDER_TEXT": _mix(base, "#FFFFFF", 0.55),
        "DIVIDER_HOVER": _mix(base, DARK["BG"], 0.2),
        "CHIP": _rgba(base, 0.16),
        "CHIP_HOVER": _rgba(base, 0.26),
    }


SCHEME = "dark"
ACCENT_KEY = APP_ACCENT
globals().update(DARK)


def use(scheme: str, accent: str | None = None) -> None:
    """Switch every color token to the dark or light set, in the chosen accent (None keeps the current one;
    an unknown or empty one means Bodega's own)."""
    global SCHEME, ACCENT_KEY
    SCHEME = "light" if scheme == "light" else "dark"
    if accent is not None:
        ACCENT_KEY = accent if accent in ACCENTS else APP_ACCENT
    globals().update(LIGHT if SCHEME == "light" else DARK)
    if ACCENT_KEY != APP_ACCENT:
        _name, dark, light = ACCENTS[ACCENT_KEY]
        globals().update(accent_set(light if SCHEME == "light" else dark, SCHEME))


def accent_of(key: str, scheme: str | None = None) -> str:
    """A choice's color in the dark or light look (the current one by default)."""
    _name, dark, light = ACCENTS.get(key, ACCENTS[APP_ACCENT])
    return light if (scheme or SCHEME) == "light" else dark
